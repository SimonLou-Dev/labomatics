#!/usr/bin/env python3
"""
Commande ``recreate`` — recrée la VM OpenWrt d'un étudiant.

Détruit la VM existante et la redéploie depuis la template.
"""

from rich.console import Console

from ..config import load_config
from ..deploy import deploy_student, destroy_student
from ..proxmox import get_pool_vms
from ._helpers import ask_confirm, load_students_from_config, make_connection

console = Console()


def cmd_recreate(args) -> None:
    """Recrée la VM OpenWrt d'un étudiant (destroy + redeploy)."""
    config = load_config()
    proxmox = make_connection()
    nom = args.nom

    # Trouver l'étudiant
    students = load_students_from_config(config)
    student = next((s for s in students if s.nom == nom), None)
    if not student:
        console.print(f"[red]❌ Étudiant '{nom}' introuvable dans le CSV.[/red]")
        return

    # Trouver la VM existante
    vms = get_pool_vms(proxmox, student.pool_name())
    openwrt_vmid = student.vmid(config.openwrt.vmid_start)

    existing_vm = next((v for v in vms if v.get("vmid") == openwrt_vmid), None)

    if existing_vm:
        console.print(
            f"[bold]Étudiant :[/bold] {student.nom}\n"
            f"[bold]VM VMID  :[/bold] {openwrt_vmid}  nœud={existing_vm.get('node')}"
        )
        if not getattr(args, "yes", False):
            if not ask_confirm(
                f"Recréer la VM de {student.nom} ? (la VM sera détruite puis redéployée)"
            ):
                console.print("[dim]Annulé.[/dim]")
                return

        console.print(f"\n[bold red]Suppression de la VM {openwrt_vmid}...[/bold red]")
        destroy_student(proxmox, existing_vm["node"], openwrt_vmid, student.vm_name())
    else:
        console.print(
            f"[yellow]⚠  Aucune VM trouvée pour {student.nom} (vmid={openwrt_vmid}), déploiement direct.[/yellow]"
        )

    console.print(f"\n[bold green]Déploiement de {student.nom}...[/bold green]")
    deploy_student(proxmox, config, student)

    console.print(f"\n[bold green]✓ {student.nom} recréé avec succès.[/bold green]\n")
