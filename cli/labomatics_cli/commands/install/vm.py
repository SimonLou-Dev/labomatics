"""VM deployment."""

import urllib.parse

from ...utils.proxmox import ProxmoxClient
from ...utils.verify import ServiceVerifier
from ...utils.state import InstallState
from ...utils.theme import info, success

from .helpers import allocate_first_wan_ip


class VMDeployer:
    """Déploiement de la VM."""

    def __init__(self, pve: ProxmoxClient, node: str, state: InstallState):
        """Initialiser."""
        self.pve = pve
        self.node = node
        self.state = state

    def deploy(
        self,
        vm_name: str,
        memory: int,
        cores: int,
        storage: str,
        image_filename: str,
        wan_config: dict,
        vm_password: str,
        ssh_pubkeys: str,
    ) -> str:
        """Déployer la VM et retourner son IP."""
        existing = self.pve.find_vm_by_name(self.node, vm_name)
        if existing:
            vmid = existing["vmid"]
            vm_ip = self.pve.get_vm_ip(self.node, vmid)
            if vm_ip:
                success(f"VM existante: {vm_name} ({vmid})")
                return vm_ip

        vmid = self.pve.get_available_vmid(self.node)
        info("Création VM...")

        boot_image = (
            f"{storage}:0,import-from={storage}:import/{image_filename},"
            f"format=qcow2,cache=writethrough,size=20G"
        )
        upid = self.pve.create_vm(
            self.node,
            vmid,
            vm_name,
            memory,
            cores,
            storage,
            ciuser="labomatics",
            boot_image=boot_image,
            cpu="x86-64-v2-AES",
        )
        if not self.pve.wait_for_task(self.node, upid, timeout=120):
            raise RuntimeError("Timeout création VM")
        success("VM créée")

        info("Redimensionnement disque...")
        self.pve.resize_disk(self.node, vmid, "scsi0", "+20G")
        success("Disque redimensionné")

        vm_ip = allocate_first_wan_ip(wan_config)
        self._configure_cloudinit(vmid, vm_ip, wan_config, vm_password, ssh_pubkeys)
        self._start_vm(vmid, vm_ip)

        self.state.set("vmid", vmid)
        self.state.set("vm_ip", vm_ip)
        return vm_ip

    def _configure_cloudinit(self, vmid, vm_ip, wan_config, password, ssh_pubkeys):
        """Configurer cloud-init."""
        info("Configuration cloud-init...")
        sshkeys_encoded = urllib.parse.quote(ssh_pubkeys, safe="")
        ipconfig0 = f"ip={vm_ip}/24,gw={wan_config['gateway']}"

        self.pve.set_cloudinit_config(
            self.node,
            vmid,
            username="labomatics",
            password=password,
            sshkeys=sshkeys_encoded,
            ipconfig0=ipconfig0,
            ciupgrade=False,
        )
        self.pve.enable_qemu_agent(self.node, vmid)
        success("cloud-init configuré")

    def _start_vm(self, vmid, vm_ip):
        """Démarrer la VM et attendre SSH."""
        info("Démarrage VM...")
        upid = self.pve.start_vm(self.node, vmid)
        self.pve.wait_for_task(self.node, upid)
        success("VM démarrée")

        info("Attente SSH...")
        ServiceVerifier.wait_for_ssh(vm_ip, timeout=300)
        success("SSH prêt")
