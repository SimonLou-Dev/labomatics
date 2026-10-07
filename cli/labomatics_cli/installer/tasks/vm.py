"""Tâche 3 : VM Labomatics (Fedora Cloud + cloud-init)."""

from __future__ import annotations

import ipaddress
from typing import Optional
from urllib.parse import quote

from labomatics_cli.installer.context import VM_USER, InstallContext
from labomatics_cli.installer.secrets import PasswordGenerator
from labomatics_cli.installer.tasks.base import InstallTask

IMAGE_FILENAME = "Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2"
IMAGE_URL = (
    "https://download.fedoraproject.org/pub/fedora/linux/releases/44/"
    f"Cloud/x86_64/images/{IMAGE_FILENAME}"
)
DISK_SIZE = "50G"
DOWNLOAD_TIMEOUT = 1800


class VmTask(InstallTask):
    """Télécharge l'image, crée la VM, configure cloud-init, la démarre et attend SSH."""

    name = "vm"
    label = "VM Labomatics"

    def run(self, ctx: InstallContext) -> None:
        """Crée la VM si elle n'existe pas, s'assure qu'elle tourne et que SSH répond.

        Args:
            ctx: Contexte d'installation.
        """
        assert ctx.config.vm is not None
        api = ctx.proxmox
        existing = api.find_vm(ctx.config.vm.name)
        if existing is None:
            vmid, node = self._create(ctx)
            status = "stopped"
        else:
            vmid, node, status = existing.vmid, existing.node, existing.status
            ctx.log(f"VM existante réutilisée ({vmid} sur {node})", "ok")
        ctx.store.set_data("vmid", vmid)
        ctx.store.set_data("vm_node", node)
        if status != "running":
            ctx.log("Démarrage de la VM")
            api.wait_task(api.start_vm(node, vmid))
        ctx.log(f"Attente de SSH sur {ctx.config.vm.vm_ip}")
        ctx.vm_ssh.run("true")
        ctx.log("SSH prêt", "ok")

    def _node(self, ctx: InstallContext) -> str:
        """Choisit le nœud hôte.

        Args:
            ctx: Contexte d'installation.

        Returns:
            Le nœud configuré, sinon le premier nœud en ligne.

        Raises:
            RuntimeError: Si aucun nœud n'est en ligne.
        """
        assert ctx.config.vm is not None
        if ctx.config.vm.node:
            return ctx.config.vm.node
        online = [n.name for n in ctx.proxmox.nodes() if n.online]
        if not online:
            raise RuntimeError("Aucun nœud Proxmox en ligne pour héberger la VM")
        return online[0]

    def _ensure_image(self, ctx: InstallContext, node: str, storage: str) -> None:
        """Fait télécharger l'image Fedora par Proxmox si elle est absente du stockage.

        Args:
            ctx: Contexte d'installation.
            node: Nœud qui télécharge.
            storage: Stockage partagé de destination.
        """
        api = ctx.proxmox
        if api.has_import_image(node, storage, IMAGE_FILENAME):
            ctx.log("Image Fedora déjà présente sur le stockage", "ok")
            return
        ctx.log("Téléchargement de l'image Fedora Cloud par Proxmox")
        api.wait_task(
            api.download_image(node, storage, IMAGE_URL, IMAGE_FILENAME),
            timeout=DOWNLOAD_TIMEOUT,
        )
        ctx.log("Image téléchargée", "ok")

    def _password(self, ctx: InstallContext) -> str:
        """Mot de passe de l'utilisateur de la VM, généré une seule fois.

        Args:
            ctx: Contexte d'installation.

        Returns:
            Le mot de passe conservé dans le store.
        """
        password: Optional[str] = ctx.store.get_data("vm_password")
        if not password:
            password = PasswordGenerator().generate()
            ctx.store.set_data("vm_password", password)
        return password

    def _options(self, ctx: InstallContext, storage: str, password: str) -> dict:
        """Construit les options de création de la VM.

        Args:
            ctx: Contexte d'installation.
            storage: Stockage des disques.
            password: Mot de passe de l'utilisateur.

        Returns:
            Les options Proxmox (matériel, disque importé, cloud-init).
        """
        vm = ctx.config.vm
        assert vm is not None
        prefix = ipaddress.ip_network(vm.admin_network, strict=False).prefixlen
        keys = [*vm.ssh_keys, ctx.key.public_key()]
        return {
            "name": vm.name,
            "memory": vm.memory,
            "cores": vm.cores,
            "sockets": 1,
            "cpu": "x86-64-v2-AES",
            "ostype": "l26",
            "bios": "ovmf",
            "machine": "q35",
            "efidisk0": f"{storage}:1",
            "scsihw": "virtio-scsi-pci",
            "scsi0": f"{storage}:0,import-from={storage}:import/{IMAGE_FILENAME}",
            "boot": "order=scsi0",
            "ide2": f"{storage}:cloudinit",
            "net0": f"virtio,bridge={vm.admin_iface}",
            "agent": "enabled=1",
            "tags": "labomatics-system",
            "onboot": 1,
            "ciuser": VM_USER,
            "cipassword": password,
            "sshkeys": quote("\n".join(keys), safe=""),
            "ipconfig0": f"ip={vm.vm_ip}/{prefix},gw={vm.admin_gateway}",
            "nameserver": " ".join(vm.dns_upstream),
            "searchdomain": vm.domain,
            "ciupgrade": 0,
        }

    def _create(self, ctx: InstallContext) -> tuple[int, str]:
        """Crée la VM complète et agrandit son disque.

        Args:
            ctx: Contexte d'installation.

        Returns:
            Le VMID et le nœud hôte.
        """
        assert ctx.config.vxlan is not None
        api = ctx.proxmox
        node = self._node(ctx)
        storage = ctx.config.vxlan.storage
        self._ensure_image(ctx, node, storage)
        vmid = api.next_vmid()
        ctx.log(f"Création de la VM {vmid} sur {node}")
        options = self._options(ctx, storage, self._password(ctx))
        api.wait_task(api.create_vm(node, vmid, **options), timeout=600)
        api.resize_disk(node, vmid, "scsi0", DISK_SIZE)
        ctx.log("VM créée", "ok")
        return vmid, node
