"""Tâche 3 : VM Labomatics (Fedora Cloud + cloud-init)."""

from __future__ import annotations

import ipaddress
from urllib.parse import quote

from labomatics_cli.installer.context import VM_USER, InstallContext
from labomatics_cli.installer.download import RemoteDownload
from labomatics_cli.installer.ssh import SshError, SshSession
from labomatics_cli.installer.tasks.base import InstallTask

IMAGE_FILENAME = "Fedora-Cloud-Base-44.qcow2"
IMAGE_URL = (
    "https://download.fedoraproject.org/pub/fedora/linux/releases/44/"
    "Cloud/x86_64/images/Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2"
)
IMAGE_CACHE = "/var/lib/labomatics/images"
DISK_SIZE = "50G"
DOWNLOAD_TIMEOUT = 1800
IMPORT_TIMEOUT = 1800


class VmTask(InstallTask):
    """Télécharge l'image, crée la VM, configure cloud-init, la démarre et attend SSH."""

    name = "vm"
    label = "VM Labomatics"
    download_poll: float = 30

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
        self._grow_filesystem(ctx)

    def _grow_filesystem(self, ctx: InstallContext) -> None:
        """Agrandit la partition racine et le système de fichiers btrfs de la VM.

        Idempotent : `growpart` répond « NOCHANGE » quand la partition est déjà à la taille du disque.

        Args:
            ctx: Contexte d'installation.

        Raises:
            SshError: Si `growpart` échoue pour une autre raison que NOCHANGE.
        """
        ssh = ctx.vm_ssh
        disk = ssh.run(
            "lsblk -no PKNAME $(findmnt -no SOURCE / | sed 's/\\[.*//')"
        ).stdout.strip()
        device = f"/dev/{disk or 'sda'}"
        result = ssh.run(f"sudo growpart {device} 3", check=False)
        if not result.ok and "NOCHANGE" not in result.stdout + result.stderr:
            raise SshError(f"growpart a échoué : {result.stderr or result.stdout}")
        ssh.run("sudo btrfs filesystem resize max /")
        ctx.log("Partition et système de fichiers agrandis", "ok")

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

    def _ensure_image(self, ctx: InstallContext, ssh: SshSession) -> str:
        """Télécharge l'image Fedora dans le cache du nœud si elle est absente.

        Args:
            ctx: Contexte d'installation.
            ssh: Session SSH sur le nœud hôte, où l'image est téléchargée.

        Returns:
            Le chemin de l'image sur le nœud.
        """
        path = f"{IMAGE_CACHE}/{IMAGE_FILENAME}"
        if ssh.run(f"test -f {path}", check=False).ok:
            ctx.log("Image Fedora déjà présente sur le nœud", "ok")
            return path
        ctx.log("Téléchargement de l'image Fedora Cloud sur le nœud")
        RemoteDownload(
            ssh, IMAGE_URL, path, poll=self.download_poll, timeout=DOWNLOAD_TIMEOUT
        ).run(ctx.log)
        ctx.log("Image téléchargée", "ok")
        return path

    def _hardware(self, ctx: InstallContext, storage: str) -> dict:
        """Construit les options matérielles de la VM vide.

        Args:
            ctx: Contexte d'installation.
            storage: Stockage des disques.

        Returns:
            Les options Proxmox de création (sans disque système).
        """
        vm = ctx.config.vm
        assert vm is not None
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
            "ide2": f"{storage}:cloudinit",
            "net0": f"virtio,bridge={vm.admin_iface}",
            "agent": "enabled=1",
            "tags": "labomatics-system",
            "onboot": 1,
        }

    def _cloud_init(self, ctx: InstallContext) -> dict:
        """Construit les options cloud-init (utilisateur, SSH, réseau).

        Args:
            ctx: Contexte d'installation.

        Returns:
            Les options Proxmox cloud-init.
        """
        vm = ctx.config.vm
        assert vm is not None
        prefix = ipaddress.ip_network(vm.admin_network, strict=False).prefixlen
        keys = [*vm.ssh_keys, ctx.key.public_key()]
        return {
            "ciuser": VM_USER,
            "cipassword": ctx.store.secrets.vm_password,
            "sshkeys": quote("\n".join(keys), safe=""),
            "ipconfig0": f"ip={vm.vm_ip}/{prefix},gw={vm.admin_gateway}",
            "nameserver": " ".join(vm.dns_upstream),
            "searchdomain": vm.domain,
            "ciupgrade": 0,
        }

    def _create(self, ctx: InstallContext) -> tuple[int, str]:
        """Crée la VM vide, y importe l'image, attache le disque et configure cloud-init.

        Args:
            ctx: Contexte d'installation.

        Returns:
            Le VMID et le nœud hôte.
        """
        assert ctx.config.vxlan is not None
        api = ctx.proxmox
        node = self._node(ctx)
        storage = ctx.config.vxlan.storage
        node_ssh = ctx.node_ssh(node)
        image = self._ensure_image(ctx, node_ssh)
        vmid = api.next_vmid()
        ctx.log(f"Création de la VM {vmid} sur {node}")
        api.wait_task(
            api.create_vm(node, vmid, **self._hardware(ctx, storage)), timeout=600
        )
        ctx.log("Import du disque système")
        node_ssh.run(
            f"qm importdisk {vmid} {image} {storage} --format qcow2",
            timeout=IMPORT_TIMEOUT,
        )
        api.attach_unused_disk(node, vmid, "scsi0")
        api.resize_disk(node, vmid, "scsi0", DISK_SIZE)
        api.set_vm_config(node, vmid, **self._cloud_init(ctx))
        ctx.log("VM créée", "ok")
        return vmid, node
