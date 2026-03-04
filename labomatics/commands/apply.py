#!/usr/bin/env python3
"""
Commandes ``apply`` et ``diff`` — synchronisation Proxmox ↔ CSV.

``diff``  : affiche les changements sans rien modifier.
``apply`` : applique les changements après confirmation.
"""

from rich.console import Console

from ..config import load_config
from ..credentials import (
    generate_password,
    load_credentials,
    make_credential,
    save_credentials,
)
from ..deploy import apply_pool_flavor, destroy_all_pool_members
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
    list_managed_pools,
    list_vnets_in_zone,
    set_student_acls,
    user_exists,
)
from ._helpers import ask_confirm, load_students_from_config, make_connection

console = Console()


def _resolve_vnet_for_pool(proxmox, config, pool_name: str) -> str | None:
    """Trouve le nom du VNet SDN d'un pool (depuis les VMs du pool ou les VNets)."""
    from ..proxmox import get_pool_vms

    vmid_start = config.openwrt.vmid_start
    for vm in get_pool_vms(proxmox, pool_name):
        vmid = vm.get("vmid")
        if vmid:
            student_id = vmid - vmid_start
            vnet_candidate = f"vn{student_id:05d}"
            return vnet_candidate
    # Fallback : chercher par alias dans la zone
    zone = config.openwrt.network.zone_name
    all_vnets = list_vnets_in_zone(proxmox, zone)
    vnet = next(
        (v["vnet"] for v in all_vnets if v.get("alias") == pool_name),
        None,
    )
    return vnet


def apply_removes(proxmox, config, to_remove: list[dict]) -> None:
    """Supprime les ressources Proxmox des étudiants retirés du CSV.

    Ordre : VMs QEMU + LXC → ACL → utilisateur → VNet → pool
    """
    if not to_remove:
        return
    console.print("\n[bold red]Suppression...[/bold red]")

    for pool in to_remove:
        pool_name = pool["poolid"]
        console.print(f"\n  [dim]Pool : {pool_name}[/dim]")

        # 1. Supprimer toutes les VMs QEMU et LXC du pool
        destroy_all_pool_members(proxmox, pool_name)

        # 2. Trouver et supprimer le VNet associé
        vnet_name = _resolve_vnet_for_pool(proxmox, config, pool_name)

        # 3. Supprimer les ACL
        delete_student_acls(proxmox, config, pool_name, vnet_name)

        # 4. Supprimer l'utilisateur Proxmox
        userid = f"{pool_name}@pve"
        if user_exists(proxmox, userid):
            try:
                delete_proxmox_user(proxmox, userid)
                console.print(f"  [red]✖ user {userid} supprimé[/red]")
            except Exception as e:
                console.print(f"  [yellow]⚠  user {userid} : {e}[/yellow]")

        # 5. Supprimer le VNet SDN
        if vnet_name:
            try:
                delete_vnet(proxmox, vnet_name)
                console.print(f"  [red]✖ vnet {vnet_name} supprimé[/red]")
            except Exception as e:
                console.print(f"  [yellow]⚠  vnet {vnet_name} : {e}[/yellow]")

        # 6. Supprimer le pool
        try:
            delete_pool(proxmox, pool_name)
            console.print(f"  [red]✖ pool {pool_name} supprimé[/red]")
        except Exception as e:
            console.print(f"  [yellow]⚠  pool {pool_name} : {e}[/yellow]")

    try:
        apply_sdn(proxmox)
    except Exception as e:
        console.print(f"  [yellow]⚠  apply SDN : {e}[/yellow]")


def apply_adds(proxmox, config, to_add: list, creds: dict) -> dict:
    """Crée les ressources Proxmox pour les nouveaux étudiants.

    Ordre : pool → VNet → apply SDN → user + ACL → credentials → VM

    Returns:
        Dict des credentials mis à jour (y compris les nouveaux).
    """
    from ..deploy import deploy_student
    from ..ip_pool import allocate_vxlan_subnet

    if not to_add:
        return creds

    console.print("\n[bold green]Création...[/bold green]")
    zone = config.openwrt.network.zone_name

    if not check_sdn_zone_exists(proxmox, zone):
        console.print(
            f"[red]❌ Zone SDN '{zone}' introuvable — créer la zone avant d'appliquer[/red]"
        )
        return creds

    # Étape 1 : pools + VNets
    for student in to_add:
        console.print(f"\n  [dim]Étudiant : {student.nom}[/dim]")
        try:
            create_pool(proxmox, student.pool_name())
            console.print(f"  [green]✓ pool {student.pool_name()}[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠  pool {student.pool_name()} : {e}[/yellow]")

        try:
            vxlan_gw, vxlan_subnet = allocate_vxlan_subnet(proxmox, config)
            create_vnet(
                proxmox,
                vnet_name=student.vnet_name(),
                zone=zone,
                tag=student.id,
                alias=student.vnet_alias(),
                gateway=vxlan_gw,
                subnet=vxlan_subnet,
            )
            console.print(f"  [green]✓ vnet {student.vnet_name()}  ({vxlan_subnet})[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠  vnet {student.vnet_name()} : {e}[/yellow]")

    # Étape 2 : apply SDN
    try:
        apply_sdn(proxmox)
        console.print("\n  [green]✓ SDN appliqué[/green]")
    except Exception as e:
        console.print(f"\n  [yellow]⚠  apply SDN : {e}[/yellow]")

    # Étape 3 : users + ACL + quotas pool
    for student in to_add:
        password = creds.get(student.nom, {}).get("password") or generate_password()
        try:
            if not user_exists(proxmox, student.user_id()):
                create_proxmox_user(proxmox, student.user_id(), password, comment="labomatics")
                console.print(f"  [green]✓ user {student.user_id()}[/green]")
            set_student_acls(proxmox, config, student)
        except Exception as e:
            console.print(f"  [yellow]⚠  user/acl {student.nom} : {e}[/yellow]")

        try:
            apply_pool_flavor(proxmox, config, student)
        except Exception as e:
            console.print(f"  [yellow]⚠  flavor {student.nom} : {e}[/yellow]")

        # Pré-enregistrer les credentials avec WAN IP = "pending"
        creds[student.nom] = make_credential(student, password, "pending")

    # Étape 4 : déploiement des VMs
    for student in to_add:
        try:
            deploy_student(proxmox, config, student)
            # Mettre à jour la WAN IP réelle dans les credentials
            from ..proxmox import get_pool_vms, get_vm_wan_ip

            for vm in get_pool_vms(proxmox, student.pool_name()):
                ip = get_vm_wan_ip(proxmox, vm["node"], vm["vmid"])
                if ip:
                    creds[student.nom]["wan_ip"] = ip
                    break
        except Exception as e:
            console.print(f"  [red]❌ deploy {student.nom} : {e}[/red]")

    return creds


def cmd_diff(args) -> None:
    """Affiche le diff CSV ↔ Proxmox sans rien modifier."""
    config = load_config()
    proxmox = make_connection()
    students = load_students_from_config(config)
    pools = list_managed_pools(proxmox)
    to_add, to_remove = compute_diff(pools, students)
    print_diff(to_add, to_remove, config, console)


def cmd_apply(args) -> None:
    """Synchronise Proxmox avec le CSV (diff + confirmation + apply)."""
    config = load_config()
    proxmox = make_connection()
    students = load_students_from_config(config)
    pools = list_managed_pools(proxmox)
    to_add, to_remove = compute_diff(pools, students)
    print_diff(to_add, to_remove, config, console)

    if not to_add and not to_remove:
        return

    if not getattr(args, "yes", False):
        if not ask_confirm("Appliquer ces changements ?"):
            console.print("[dim]Annulé.[/dim]")
            return

    creds = load_credentials(config)

    if to_remove:
        apply_removes(proxmox, config, to_remove)
        # Nettoyer les credentials des étudiants supprimés
        removed_names = {p["poolid"] for p in to_remove}
        creds = {k: v for k, v in creds.items() if k not in removed_names}

    creds = apply_adds(proxmox, config, to_add, creds)

    path = save_credentials(config, creds)
    console.print(f"\n[bold]Credentials sauvegardés → {path}[/bold]")
    console.print("\n[bold green]✓ Apply terminé[/bold green]\n")
