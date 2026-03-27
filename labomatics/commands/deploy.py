#!/usr/bin/env python3
"""
Commandes ``deploy`` et ``undeploy`` — déploiement de TPs par groupe d'étudiants.

Pipeline deploy pour chaque (étudiant × VM) :
1. Vérification si la VM existe déjà (via tag Proxmox + marker description)
2. Si elle existe et que le config_hash est identique → ignorée
3. Si le hash diffère → suppression + recréation
4. Clone de la template source → configuration mémoire/CPU/réseau/cloud-init
5. net0 = VNet VXLAN de l'étudiant (toujours) ; net1+ = extra_nics optionnels
6. Tag ``labomatics-tp:{tp_name}`` + marker dans la description
7. Ajout au pool de l'étudiant
8. Démarrage si start=True

Format du marker description (section protégée) :
    --- labomatics ---
    tp: mon-tp
    student_id: 18
    vm: router
    config_hash: a3f9c2d1
    --- end labomatics ---
"""

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from rich.console import Console

from ..config import load_config, load_tp_config
from ..deploy import destroy_student
from ..proxmox import (
    add_vm_to_pool,
    find_tp_vms,
    find_vm_node,
    get_vm_description,
    pick_node,
    wait_for_task,
)
from ._helpers import ask_confirm, load_students_from_config, make_connection

if TYPE_CHECKING:
    from ..config import TpConfig, TpVmConfig
    from ..students import Student

console = Console()

# Verrou pour l'acquisition du VMID (évite la race condition entre workers)
_vmid_lock = threading.Lock()

_MARKER_START = "--- labomatics ---"
_MARKER_END = "--- end labomatics ---"


# ── Marker description ────────────────────────────────────────────────────────


def _compute_config_hash(vm_spec: "TpVmConfig") -> str:
    """Hash des paramètres déterminants d'une VM de TP (8 chars hex)."""
    data = {
        "template": vm_spec.template,
        "memory": vm_spec.memory,
        "cores": vm_spec.cores,
        "disk_size": vm_spec.disk_size,
        "cloud_init": vm_spec.cloud_init.model_dump() if vm_spec.cloud_init else None,
        "extra_nics": [n.model_dump() for n in vm_spec.extra_nics],
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:8]


def _make_description(tp_name: str, student_id: int, vm_name: str, config_hash: str) -> str:
    return (
        f"{_MARKER_START}\n"
        f"tp: {tp_name}\n"
        f"student_id: {student_id}\n"
        f"vm: {vm_name}\n"
        f"config_hash: {config_hash}\n"
        f"{_MARKER_END}"
    )


def _parse_description(description: str) -> dict | None:
    """Extrait le bloc marker de la description d'une VM. Retourne None si absent."""
    try:
        start = description.index(_MARKER_START)
        end = description.index(_MARKER_END)
    except ValueError:
        return None
    block = description[start + len(_MARKER_START) : end].strip()
    result: dict = {}
    for line in block.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            result[k.strip()] = v.strip()
    return result if result else None


# ── VM creation ───────────────────────────────────────────────────────────────


def _next_vmid(proxmox) -> int:
    """Obtient le prochain VMID disponible (thread-safe)."""
    with _vmid_lock:
        return int(proxmox.cluster.nextid.get())


def _create_tp_vm(
    proxmox,
    config,
    student: "Student",
    vm_spec: "TpVmConfig",
    tp: "TpConfig",
) -> None:
    """Clone la template et configure la VM pour un étudiant."""
    new_vmid = _next_vmid(proxmox)

    source_node = find_vm_node(proxmox, vm_spec.template)
    if source_node is None:
        raise RuntimeError(f"Template VMID {vm_spec.template} introuvable sur le cluster")
    target_node = pick_node(proxmox)

    vm_name = f"{student.login()}-{vm_spec.name}"
    storage = config.openwrt.storage

    # Clone complet
    clone_kwargs: dict = dict(
        newid=new_vmid,
        name=vm_name,
        full=1,
        storage=storage,
        pool=student.pool_name(),
    )
    if target_node != source_node:
        clone_kwargs["target"] = target_node

    try:
        task = proxmox.nodes(source_node).qemu(vm_spec.template).clone.post(**clone_kwargs)
    except Exception as e:
        if "local storage" in str(e) and "target" in clone_kwargs:
            target_node = source_node
            clone_kwargs.pop("target")
            task = proxmox.nodes(source_node).qemu(vm_spec.template).clone.post(**clone_kwargs)
        else:
            raise
    wait_for_task(proxmox, source_node, task)

    # Configuration post-clone
    cfg_kwargs: dict = dict(
        memory=vm_spec.memory,
        cores=vm_spec.cores,
        net0=f"virtio,bridge={student.vnet_name()}",
    )

    # Interfaces supplémentaires
    for i, nic in enumerate(vm_spec.extra_nics, start=1):
        cfg_kwargs[f"net{i}"] = f"{nic.model},bridge={nic.bridge}"

    # Cloud-init
    if vm_spec.cloud_init is not None:
        cfg_kwargs["ide2"] = f"{storage}:cloudinit"
        cfg_kwargs["ipconfig0"] = "ip=dhcp"
        if vm_spec.cloud_init.user:
            cfg_kwargs["ciuser"] = vm_spec.cloud_init.user
        if vm_spec.cloud_init.password:
            cfg_kwargs["cipassword"] = vm_spec.cloud_init.password

    # Tags Proxmox : tp marker + tags utilisateur
    all_tags = [f"labomatics-tp:{tp.name}"] + tp.tags
    cfg_kwargs["tags"] = ";".join(all_tags)

    # Description marker (idempotence)
    config_hash = _compute_config_hash(vm_spec)
    cfg_kwargs["description"] = _make_description(tp.name, student.id, vm_spec.name, config_hash)

    proxmox.nodes(target_node).qemu(new_vmid).config.put(**cfg_kwargs)

    # Redimensionnement disque
    if vm_spec.disk_size:
        try:
            proxmox.nodes(target_node).qemu(new_vmid).resize.put(
                disk="scsi0", size=vm_spec.disk_size
            )
        except Exception as e:
            console.print(f"  [yellow]⚠  resize disque {vm_name} : {e}[/yellow]")

    # Pool (le clone l'ajoute déjà via pool=, mais on s'assure)
    try:
        add_vm_to_pool(proxmox, student.pool_name(), new_vmid)
    except Exception:
        pass

    # Démarrage
    if vm_spec.start:
        task = proxmox.nodes(target_node).qemu(new_vmid).status.start.post()
        wait_for_task(proxmox, target_node, task)

    console.print(f"  [green]✓ {vm_name:35} vmid={new_vmid}  node={target_node}[/green]")


# ── Deploy / undeploy par étudiant ────────────────────────────────────────────


def _find_existing_vm(proxmox, tp_name: str, student_id: int, vm_name: str) -> dict | None:
    """Cherche une VM existante pour ce (tp, student, vm) dans les resources du cluster."""
    for r in find_tp_vms(proxmox, tp_name):
        desc = get_vm_description(proxmox, r["node"], r["vmid"])
        marker = _parse_description(desc)
        if (
            marker
            and int(marker.get("student_id", -1)) == student_id
            and marker.get("vm") == vm_name
        ):
            marker["_resource"] = r
            return marker
    return None


def _process_student(proxmox, config, student: "Student", tp: "TpConfig") -> None:
    """Déploie toutes les VMs du TP pour un étudiant (séquentiel)."""
    for vm_spec in tp.vms:
        existing = _find_existing_vm(proxmox, tp.name, student.id, vm_spec.name)
        vm_label = f"{student.login()}-{vm_spec.name}"

        if existing:
            current_hash = existing.get("config_hash", "")
            expected_hash = _compute_config_hash(vm_spec)
            if current_hash == expected_hash:
                console.print(f"  [dim]↷ {vm_label:35} déjà à jour[/dim]")
                continue
            # Config modifiée → supprimer et recréer
            r = existing["_resource"]
            console.print(f"  [yellow]↻ {vm_label:35} config modifiée → recréation[/yellow]")
            destroy_student(proxmox, r["node"], r["vmid"], vm_label)
            time.sleep(1)

        _create_tp_vm(proxmox, config, student, vm_spec, tp)


# ── Commandes CLI ─────────────────────────────────────────────────────────────


def cmd_deploy(args) -> None:
    """Déploie (ou met à jour) les VMs d'un TP pour les étudiants ciblés."""
    config = load_config()
    proxmox = make_connection()
    tp = load_tp_config(args.file)

    all_students = load_students_from_config(config)
    if tp.target_classes is not None:
        students = [s for s in all_students if s.classe in tp.target_classes]
    else:
        students = all_students

    if not students:
        console.print("[yellow]Aucun étudiant correspondant aux classes cibles.[/yellow]")
        return

    total_vms = len(students) * len(tp.vms)
    console.print(
        f"\n[bold cyan]Deploy TP :[/bold cyan] {tp.name}  "
        f"— {len(students)} étudiant(s) × {len(tp.vms)} VM(s) = {total_vms} VM(s)"
    )
    if tp.target_classes:
        console.print(f"  [dim]Classes : {', '.join(tp.target_classes)}[/dim]")

    if not getattr(args, "yes", False):
        if not ask_confirm(f"Déployer {total_vms} VM(s) ?"):
            console.print("[dim]Annulé.[/dim]")
            return

    workers = getattr(args, "workers", 1)

    def _task(student: "Student") -> None:
        _process_student(proxmox, config, student, tp)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_task, s): s for s in students}
        for future in as_completed(futures):
            student = futures[future]
            try:
                future.result()
            except Exception as e:
                console.print(f"[red]❌ {student.nom} : {e}[/red]")

    console.print(f"\n[bold green]✓ Deploy TP '{tp.name}' terminé[/bold green]\n")


def cmd_undeploy(args) -> None:
    """Supprime toutes les VMs d'un TP (depuis fichier ou nom)."""
    proxmox = make_connection()

    if getattr(args, "file", None):
        tp = load_tp_config(args.file)
        tp_name = tp.name
    else:
        tp_name = args.tp

    resources = find_tp_vms(proxmox, tp_name)
    if not resources:
        console.print(f"[yellow]Aucune VM trouvée pour le TP '{tp_name}'.[/yellow]")
        return

    console.print(f"\n[bold red]Undeploy TP :[/bold red] {tp_name}  — {len(resources)} VM(s)")

    if not getattr(args, "yes", False):
        if not ask_confirm(f"Supprimer {len(resources)} VM(s) ?"):
            console.print("[dim]Annulé.[/dim]")
            return

    workers = getattr(args, "workers", 2)

    def _delete(r: dict) -> None:
        destroy_student(proxmox, r["node"], r["vmid"], r.get("name", str(r["vmid"])))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_delete, r) for r in resources]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                console.print(f"[red]❌ {e}[/red]")

    console.print(f"\n[bold green]✓ Undeploy TP '{tp_name}' terminé[/bold green]\n")
