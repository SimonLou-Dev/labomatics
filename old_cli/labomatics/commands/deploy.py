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
import re
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn

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

# _vmid_lock couvre nextid() + clone POST (pas le wait).
# Une fois le POST envoyé, Proxmox crée le fichier de config → le prochain
# nextid() retourne un VMID différent. Le wait_for_task se fait hors du lock
# → plusieurs clones progressent en parallèle, Proxmox sérialise par template.
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


def _create_tp_vm(
    proxmox,
    config,
    student: "Student",
    vm_spec: "TpVmConfig",
    tp: "TpConfig",
    update: "Callable[[str], None]",
) -> tuple[int, str]:
    """Clone la template et configure la VM. Retourne (new_vmid, target_node).

    Locking :
    - _vmid_lock global court : nextid() seulement (évite doublons de VMID)
    - _get_clone_lock(template) : clone POST + wait sérialisés par template source
      → deux templates différentes peuvent cloner en parallèle
    - Configuration post-clone entièrement hors des locks
    """
    source_node = find_vm_node(proxmox, vm_spec.template)
    if source_node is None:
        raise RuntimeError(f"Template VMID {vm_spec.template} introuvable sur le cluster")
    target_node = pick_node(proxmox)
    vm_name = f"{student.login()}-{vm_spec.name}"
    storage = config.openwrt.storage

    # VMID + clone POST sous le même verrou : nextid() ne réserve pas le VMID,
    # Proxmox le fait seulement quand il crée le fichier de config (à la réception du POST).
    # Le wait_for_task se fait hors du verrou → plusieurs clones progressent en parallèle.
    update(f"clone depuis {vm_spec.template}…")
    clone_kwargs: dict = dict(
        newid=0, name=vm_name, full=1, storage=storage, pool=student.pool_name()
    )
    if target_node != source_node:
        clone_kwargs["target"] = target_node

    with _vmid_lock:
        new_vmid = int(proxmox.cluster.nextid.get())
        clone_kwargs["newid"] = new_vmid
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

    # Étapes 3+ : configuration post-clone (hors de tout verrou)
    try:
        update("configuration réseau…")
        vm_cfg = proxmox.nodes(target_node).qemu(new_vmid).config.get()

        cfg_kwargs: dict = dict(
            memory=vm_spec.memory,
            cores=vm_spec.cores,
            net0=f"virtio,bridge={student.vnet_name()}",
        )
        for i, nic in enumerate(vm_spec.extra_nics, start=1):
            cfg_kwargs[f"net{i}"] = f"{nic.model},bridge={nic.bridge}"

        if vm_spec.cloud_init is not None:
            has_cloudinit = any(
                "cloudinit" in str(vm_cfg.get(k, ""))
                for k in vm_cfg
                if k.startswith(("ide", "sata", "scsi", "virtio"))
            )
            if not has_cloudinit:
                cfg_kwargs["ide2"] = f"{storage}:cloudinit"
            cfg_kwargs["ipconfig0"] = "ip=dhcp"
            if vm_spec.cloud_init.user:
                cfg_kwargs["ciuser"] = vm_spec.cloud_init.user
            if vm_spec.cloud_init.password:
                cfg_kwargs["cipassword"] = vm_spec.cloud_init.password

        def _sanitize_tag(t: str) -> str:
            return re.sub(r"[^a-zA-Z0-9_\-]", "-", t)

        all_tags = [_sanitize_tag(f"labomatics-tp--{tp.name}")] + [
            _sanitize_tag(t) for t in tp.tags
        ]
        cfg_kwargs["tags"] = ";".join(all_tags)
        cfg_kwargs["description"] = _make_description(
            tp.name, student.id, vm_spec.name, _compute_config_hash(vm_spec)
        )
        proxmox.nodes(target_node).qemu(new_vmid).config.put(**cfg_kwargs)

        if vm_spec.disk_size:
            update(f"resize → {vm_spec.disk_size}…")
            _DISK_KEYS = ("virtio", "scsi", "sata", "ide")
            boot_disk = next(
                (
                    k
                    for prefix in _DISK_KEYS
                    for k in sorted(vm_cfg)
                    if k.startswith(prefix)
                    and k[len(prefix) :].isdigit()
                    and "cloudinit" not in str(vm_cfg[k])
                    and "media=cdrom" not in str(vm_cfg[k])
                ),
                None,
            )
            if boot_disk:
                proxmox.nodes(target_node).qemu(new_vmid).resize.put(
                    disk=boot_disk, size=vm_spec.disk_size
                )

        try:
            add_vm_to_pool(proxmox, student.pool_name(), new_vmid)
        except Exception:
            pass

        if vm_spec.start:
            update("démarrage…")
            task = proxmox.nodes(target_node).qemu(new_vmid).status.start.post()
            wait_for_task(proxmox, target_node, task)

    except Exception:
        update("échec — nettoyage…")
        try:
            proxmox.nodes(target_node).qemu(new_vmid).status.stop.post(skiplock=1)
            time.sleep(2)
        except Exception:
            pass
        try:
            task = proxmox.nodes(target_node).qemu(new_vmid).delete(purge=1)
            wait_for_task(proxmox, target_node, task, timeout=60)
        except Exception:
            pass
        raise

    return new_vmid, target_node


# ── Deploy / undeploy par étudiant ────────────────────────────────────────────


def _build_existing_cache(proxmox, tp_name: str) -> dict[tuple[int, str], dict]:
    """Pré-charge toutes les VMs existantes du TP en un seul appel cluster."""
    cache: dict[tuple[int, str], dict] = {}
    for r in find_tp_vms(proxmox, tp_name):
        desc = get_vm_description(proxmox, r["node"], r["vmid"])
        marker = _parse_description(desc)
        if marker:
            try:
                sid = int(marker["student_id"])
                vname = marker["vm"]
                marker["_resource"] = r
                cache[(sid, vname)] = marker
            except (KeyError, ValueError):
                pass
    return cache


def _process_vm(
    proxmox,
    config,
    student: "Student",
    vm_spec: "TpVmConfig",
    tp: "TpConfig",
    existing_cache: dict[tuple[int, str], dict],
    progress: Progress,
    tid: TaskID,
) -> None:
    """Déploie une VM de TP pour un étudiant (tâche indépendante)."""
    vm_label = f"{student.login()}-{vm_spec.name}"
    existing = existing_cache.get((student.id, vm_spec.name))

    def upd(step: str) -> None:
        progress.update(tid, step=step)

    if existing:
        if existing.get("config_hash", "") == _compute_config_hash(vm_spec):
            progress.update(tid, step="déjà à jour", completed=1)
            return
        r = existing["_resource"]
        upd("recréation — suppression…")
        destroy_student(proxmox, r["node"], r["vmid"], vm_label)
        time.sleep(1)

    new_vmid, node = _create_tp_vm(proxmox, config, student, vm_spec, tp, upd)
    progress.update(
        tid,
        description=f"[green]{vm_label}[/green]",
        step=f"vmid={new_vmid}  node={node}",
        completed=1,
    )


# ── Commandes CLI ─────────────────────────────────────────────────────────────


def cmd_deploy(args) -> None:
    """Déploie (ou met à jour) les VMs d'un TP pour les étudiants ciblés."""
    config = load_config()
    proxmox = make_connection()
    tp = load_tp_config(args.file)

    all_students = load_students_from_config(config)
    students = (
        [s for s in all_students if s.classe in tp.target_classes]
        if tp.target_classes is not None
        else all_students
    )

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

    if not getattr(args, "yes", False) and not ask_confirm(f"Déployer {total_vms} VM(s) ?"):
        console.print("[dim]Annulé.[/dim]")
        return

    console.print("  [dim]Vérification des VMs existantes…[/dim]")
    existing_cache = _build_existing_cache(proxmox, tp.name)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description:<45}"),
        TextColumn("[dim]{task.fields[step]}"),
        console=console,
        transient=False,
    ) as progress:
        # Une tâche Rich par (étudiant × VM)
        task_map: dict[tuple[int, str], TaskID] = {}
        for s in students:
            for vm_spec in tp.vms:
                label = f"{s.login()}-{vm_spec.name}"
                tid = progress.add_task(label, step="en attente…", total=1, completed=0)
                task_map[(s.id, vm_spec.name)] = tid

        errors: list[str] = []

        # Une tâche par (étudiant × VM) — parallélisme maximal
        # Clones de la même template : sérialisés via _get_clone_lock
        # Clones de templates différentes : parallèles
        # Config post-clone : entièrement parallèle
        def _task(s: "Student", vm_spec: "TpVmConfig", tid: TaskID) -> None:
            _process_vm(proxmox, config, s, vm_spec, tp, existing_cache, progress, tid)

        with ThreadPoolExecutor(max_workers=total_vms) as executor:
            futures = {
                executor.submit(_task, s, vm_spec, task_map[(s.id, vm_spec.name)]): (s, vm_spec)
                for s in students
                for vm_spec in tp.vms
            }
            for future in as_completed(futures):
                s, vm_spec = futures[future]
                try:
                    future.result()
                except Exception as e:
                    vm_label = f"{s.login()}-{vm_spec.name}"
                    errors.append(f"{vm_label} : {e}")

    if errors:
        for err in errors:
            console.print(f"[red]❌ {err}[/red]")
    else:
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

    def _delete(r: dict) -> None:
        destroy_student(proxmox, r["node"], r["vmid"], r.get("name", str(r["vmid"])))

    with ThreadPoolExecutor(max_workers=len(resources)) as executor:
        futures = [executor.submit(_delete, r) for r in resources]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                console.print(f"[red]❌ {e}[/red]")

    console.print(f"\n[bold green]✓ Undeploy TP '{tp_name}' terminé[/bold green]\n")
