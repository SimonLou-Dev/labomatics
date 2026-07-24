"""Client Proxmox simplifié pour CLI v0.4."""

from typing import Optional


class ProxmoxClient:
    """Client Proxmox minimal pour le CLI."""

    def __init__(self, url: str, user: str, token: str, token_id: str):
        """Initialiser le client."""
        self.url = url
        self.user = user
        self.token = token
        self.token_id = token_id
        # TODO: implement actual Proxmox API calls via requests

    def validate_connection(self) -> bool:
        """Valider la connexion."""
        # TODO: make test API call
        return True

    def create_vm_from_template(
        self,
        node: str,
        vmid: int,
        name: str,
        template_vmid: int,
        cores: int,
        memory: int,
        storage: str,
        disk_size: int,
    ) -> None:
        """Créer une VM à partir d'un template."""
        # TODO: implement VM cloning
        pass

    def upload_cloud_init(self, node: str, vmid: int, cloud_init_script: str) -> None:
        """Uploader un cloud-init script."""
        # TODO: implement cloud-init upload
        pass

    def start_vm(self, node: str, vmid: int) -> None:
        """Démarrer une VM."""
        # TODO: implement VM start
        pass

    def add_vm_to_ha(self, node: str, vmid: int) -> None:
        """Ajouter une VM à HA."""
        # TODO: implement HA add
        pass
