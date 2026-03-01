#!/usr/bin/env python3
"""
Commandes ``apply`` et ``diff`` — synchronisation CSV ↔ Proxmox.

``apply`` est la commande principale du script. Elle calcule le diff entre
le CSV étudiant et l'état courant du cluster Proxmox, affiche un récapitulatif,
demande confirmation, puis applique les ajouts et suppressions.

``diff`` est une version en lecture seule qui affiche le même récapitulatif
sans rien modifier.

Ordre d'opérations pour les suppressions
-----------------------------------------
1. Arrêt + suppression des VMs QEMU (``wait_for_task`` à chaque étape)
2. Arrêt + suppression des LXC
3. Révocation des ACL + suppression du compte ``nom@pve``
4. Suppression du VNet SDN + ``apply_sdn``
5. Suppression du pool Proxmox
6. Mise à jour de ``credentials.csv``

Ordre d'opérations pour les ajouts
------------------------------------
1. Création du pool + du VNet (en batch)
2. ``apply_sdn``
3. Création du compte ``nom@pve`` + ACL
4. Écriture de ``credentials.csv``
5. Clone template → cloud-init → démarrage VM
"""

import sys

from rich.console import Console

from ._helpers import (
    ask_confirm,
    load_students_from_config,
    make_connection,
)
from ..credentials import (
    generate_password,
    load_credentials,
    make_credential,
    save_credentials,
)
from ..deploy import deploy_student, destroy_lxc, destroy_student
from ..diff import compute_diff, print_diff
from ..proxmox import (
    apply_sdn,
    check_sdn_zone_exists,
    create_pool,
    create_proxmox_user,
    create_vnet,
    delete_pool,
    delete_proxmox_user,
    delete_student_acls,
    delete_vnet,
    get_pool_lxcs,
    get_pool_vms,
    list_managed_pools,
    set_student_acls,
    user_exists,
)
from ..students import Student

console = Console()


# ── Suppressions ──────────────────────────────────────────────────────────────


def apply_removes(proxmox, config, to_remove: list[dict]) -> None:
    """Supprime les ressources Proxmox des étudiants retirés du CSV.

    Args:
        proxmox: Client API Proxmox authentifié.
        config: Configuration de l'infrastructure.
        to_remove: Pools Proxmox gérés absents du CSV.
    """
    if not to_remove:
        return

    console.print("\n[bold red]Suppression...[/bold red]")
    zone = config.openwrt.network.zone_name
    all_vnets = proxmox.cluster.sdn.vnets.get()
    sdn_changed = False
    creds = load_credentials(config)

    for pool_info in to_remove:
        pool_name = pool_info["poolid"]

        # Retrouver le VNet associé (alias == pool_name)
        vnet_name = next(
            (v["vnet"] for v in all_vnets
             if v.get("zone") == zone and v.get("alias") == pool_name),
            None,
        )

        # 1. VMs QEMU — le nœud est dans les métadonnées du membre de pool
        try:
            for member in get_pool_vms(proxmox, pool_name):
                vmid = member.get("vmid")
                node = member.get("node")
                if vmid and node:
                    destroy_student(proxmox, node, vmid, member.get("name", str(vmid)))
        except Exception:
            pass

        # 2. LXC
        try:
            for member in get_pool_lxcs(proxmox, pool_name):
                vmid = member.get("vmid")
                node = member.get("node")
                if vmid and node:
                    destroy_lxc(proxmox, node, vmid, member.get("name", str(vmid)))
        except Exception:
            pass

        # 3. ACL + compte utilisateur
        delete_student_acls(proxmox, config, pool_name, vnet_name)
        try:
            delete_proxmox_user(proxmox, f"{pool_name}@pve")
            console.print(f"  [red]✖ user {pool_name}@pve — supprimé[/red]")
        except Exception as e:
            console.print(f"  [yellow]⚠  user {pool_name}@pve : {e}[/yellow]")

        # 4. VNet SDN
        if vnet_name:
            try:
                delete_vnet(proxmox, vnet_name)
                sdn_changed = True
            except Exception as e:
                console.print(f"  [yellow]⚠  vnet {vnet_name} : {e}[/yellow]")

        # 5. Pool (doit être vide à ce stade)
        try:
            delete_pool(proxmox, pool_name)
        except Exception as e:
            console.print(f"  [yellow]⚠  pool {pool_name} : {e}[/yellow]")

        # 6. Retirer des credentials
        creds.pop(pool_name, None)

    if sdn_changed:
        apply_sdn(proxmox)
        console.print("  [dim]SDN appliqué[/dim]")

    path = save_credentials(config, creds)
    console.print(f"  [dim]Credentials mis à jour → {path.name}[/dim]")


# ── Ajouts ────────────────────────────────────────────────────────────────────


def apply_adds(proxmox, config, to_add: list[Student]) -> None:
    """Crée les ressources Proxmox pour les nouveaux étudiants du CSV.

    Args:
        proxmox: Client API Proxmox authentifié.
        config: Configuration de l'infrastructure.
        to_add: Étudiants présents dans le CSV mais absents de Proxmox.
    """
    if not to_add:
        return

    console.print("\n[bold green]Déploiement...[/bold green]")
    zone = config.openwrt.network.zone_name
    wan_subnet = config.openwrt.network.wan_subnet
    vxlan_pool_cidr = config.openwrt.network.vxlan_pool

    # 1. Pools + VNets en batch (avant apply_sdn)
    for student in to_add:
        create_pool(proxmox, student.pool_name())
        create_vnet(
            proxmox,
            vnet_name=student.vnet_name(),
            zone=zone,
            tag=student.id,
            alias=student.pool_name(),
            subnet=student.vxlan_subnet(vxlan_pool_cidr),
            gateway=student.vxlan_gateway(vxlan_pool_cidr),
        )

    # 2. Application SDN
    apply_sdn(proxmox)
    console.print("  [dim]SDN appliqué[/dim]\n")

    # 3. Comptes Proxmox + ACL
    creds = load_credentials(config)
    for student in to_add:
        userid = student.user_id()
        nom = student.nom
        # Conserver le mot de passe existant si l'étudiant est déjà dans credentials.csv
        password = creds[nom]["password"] if nom in creds else generate_password()
        try:
            if not user_exists(proxmox, userid):
                create_proxmox_user(proxmox, userid, password, comment="esgilabs-managed")
            set_student_acls(proxmox, config, student)
            creds[nom] = make_credential(student, password, student.wan_ip(wan_subnet))
            console.print(f"  [dim]✓ user {userid} — ACL configurées[/dim]")
        except Exception as e:
            console.print(f"  [yellow]⚠  user {userid} : {e}[/yellow]")

    # 4. Écriture credentials.csv
    path = save_credentials(config, creds)
    console.print(f"  [dim]Credentials → {path.name}[/dim]\n")

    # 5. VMs OpenWrt
    for student in to_add:
        with console.status(f"[bold]{student.vm_name()}...[/bold]"):
            try:
                deploy_student(proxmox, config, student)
            except Exception as e:
                console.print(f"  [red]✗ {student.vm_name()} — {e}[/red]")
                raise


# ── Commandes ─────────────────────────────────────────────────────────────────


def cmd_apply(args) -> None:
    """Synchronise Proxmox avec le CSV (diff + confirmation + apply)."""
    proxmox, cfg = make_connection()
    students = load_students_from_config(cfg)

    zone = cfg.openwrt.network.zone_name
    if not check_sdn_zone_exists(proxmox, zone):
        console.print(f"[red]❌ Zone SDN '{zone}' introuvable[/red]")
        sys.exit(1)

    to_add, to_remove = compute_diff(list_managed_pools(proxmox), students)
    print_diff(to_add, to_remove, cfg, console)

    if not to_add and not to_remove:
        return

    if not args.yes and not ask_confirm():
        console.print("[yellow]Annulé.[/yellow]")
        return

    apply_removes(proxmox, cfg, to_remove)
    apply_adds(proxmox, cfg, to_add)
    console.print("\n[bold green]✓ Terminé[/bold green]\n")


def cmd_diff(_) -> None:
    """Affiche le diff CSV ↔ Proxmox sans modifier quoi que ce soit."""
    proxmox, cfg = make_connection()
    students = load_students_from_config(cfg)
    to_add, to_remove = compute_diff(list_managed_pools(proxmox), students)
    print_diff(to_add, to_remove, cfg, console)
