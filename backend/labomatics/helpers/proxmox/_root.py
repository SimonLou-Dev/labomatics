"""Wrapper principal Proxmox avec agrégation de tous les clients."""

from backend.labomatics.core.db.models.cluster import Cluster
from backend.labomatics.core.security.crypto import decrypt_secret
from backend.labomatics.helpers.proxmox.acl import ProxmoxAclClient
from backend.labomatics.helpers.proxmox.api import ProxmoxClientPool
from backend.labomatics.helpers.proxmox.pool import ProxmoxPoolClient
from backend.labomatics.helpers.proxmox.sdn import ProxmoxSDNClient
from backend.labomatics.helpers.proxmox.token import ProxmoxTokenClient
from backend.labomatics.helpers.proxmox.user import ProxmoxUserClient
from backend.labomatics.helpers.proxmox.vm import ProxmoxVMClient


class LabomaticsProxmoxClient:
    """Wrapper principal Proxmox avec tous les sous-clients.

    Crée un pool de connexions réutilisable au cluster et le partage
    avec tous les sous-clients.
    """

    def __init__(self, cluster: Cluster) -> None:
        """Initialise le wrapper Proxmox avec pool partagé.

        Args:
            cluster: Configuration du cluster (doit avoir un credential).

        Raises:
            ValueError: Si le cluster n'a pas de credential configuré.
        """
        self._cluster = cluster

        if not cluster.credential:
            raise ValueError(f"Cluster {cluster.name} has no credential configured")

        cred = cluster.credential
        self._proxmox_client: ProxmoxClientPool = ProxmoxClientPool(
            url=cluster.url,
            user=cred.user,
            token_id=cred.token_id,
            token_secret=cred.encrypted_token_secret,
            decrypt_fn=decrypt_secret,
        )

        self.acl = ProxmoxAclClient(proxmox_client=self._proxmox_client)
        self.user = ProxmoxUserClient(proxmox_client=self._proxmox_client)
        self.token = ProxmoxTokenClient(proxmox_client=self._proxmox_client)
        self.pool = ProxmoxPoolClient(proxmox_client=self._proxmox_client)
        self.sdn = ProxmoxSDNClient(proxmox_client=self._proxmox_client)
        self.vm = ProxmoxVMClient(proxmox_client=self._proxmox_client)

    async def create_user_with_deps(
        self,
        user_name: str,
        realm: str,
        zone: str,
        tag: int,
        gateway: str,
        subnet: str,
    ) -> dict:
        """Crée un utilisateur avec toutes les dépendances (token, ACL, VNet).

        Args:
            user_name: Nom d'utilisateur (partie avant @).
            realm: Realm Proxmox (ex: "pve", "ldap").
            zone: Nom de la zone SDN.
            tag: Tag VXLAN (ex: student.id, doit être unique dans la zone).
            gateway: IP de la passerelle du subnet (ex: "10.100.18.254").
            subnet: Subnet CIDR (ex: "10.100.18.0/24").

        Returns:
            Dict avec le token API créé: {"token": (full_id, secret)}.

        Raises:
            RuntimeError: Si une étape échoue (création user, pool, VNet, ACL ou token).
        """
        user_id = f"{user_name}@{realm}"
        vnet = f"labomatics_vn{tag}"

        try:
            await self.user.create(user_name=user_name, realm=realm)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to create user: {e}") from e

        try:
            await self.pool.create(
                user_name, f"Pool labomatics de l'utilisateur {user_name} vnet {vnet}"
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to create user pool: {e}") from e

        try:
            await self.sdn.create_vnet(
                vnet_name=vnet,
                zone=zone,
                tag=tag,
                alias=user_name,
                gateway=gateway,
                subnet=subnet,
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to create VNet: {e}") from e

        try:
            await self.acl.set_student(
                zone=zone, vnet=vnet, user_pool=user_name, user_id=user_id
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to set student ACLs: {e}") from e

        try:
            token = await self.token.create_student(userid=user_id)
        except RuntimeError as e:
            raise RuntimeError(f"Failed to create student token: {e}") from e

        return {"token": token}

    async def close(self) -> None:
        """Ferme le pool de connexions Proxmox."""
        await self._proxmox_client.close()
