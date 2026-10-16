"""Client Proxmox pour le firewall VM (anti-spoofing réseau).

Empêche un routeur étudiant de s'attribuer une IP WAN autre que celle qui
lui a été allouée : firewall VM actif, filtrage MAC, et IPSet `ipfilter-netX`
contenant la seule IP autorisée sur cette interface (voir issue #78).
"""

from __future__ import annotations

from labomatics.helpers.proxmox.api import (
    ProxmoxAPIError,
    ProxmoxClientPool,
    ProxmoxServerError,
    urls,
)


class ProxmoxVmFirewallClient:
    """Client pour gérer le firewall et les IPSets d'une VM Proxmox."""

    def __init__(self, proxmox_client: ProxmoxClientPool) -> None:
        """Initialise le client firewall VM.

        Args:
            proxmox_client: Pool de connexions Proxmox partagée.
        """
        self._proxmox_client: ProxmoxClientPool = proxmox_client

    async def set_vm_options(
        self,
        node: str,
        vmid: int,
        *,
        enable: bool = True,
        ipfilter: bool = True,
        macfilter: bool = True,
    ) -> None:
        """Active le firewall de la VM avec filtrage IP/MAC.

        Args:
            node: Nœud hébergeant la VM.
            vmid: ID de la VM.
            enable: Active le firewall de la VM.
            ipfilter: Restreint chaque interface à son IPSet `ipfilter-netX`.
            macfilter: Empêche l'usurpation d'adresse MAC sur les interfaces.

        Raises:
            RuntimeError: Problème API Proxmox.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                await client.put(
                    urls.qemu_firewall_options(node, vmid),
                    data={
                        "enable": int(enable),
                        "ipfilter": int(ipfilter),
                        "macfilter": int(macfilter),
                    },
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to set firewall options for VM {vmid}: {e}"
                ) from e

    async def _ensure_ipset_exists(self, node: str, vmid: int, name: str) -> None:
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(
                    urls.qemu_firewall_ipset(node, vmid), cache=False
                )
            except ProxmoxServerError as e:
                raise RuntimeError(f"Failed to list IPSets for VM {vmid}: {e}") from e

            existing = {ipset.get("name") for ipset in resp.get("data", [])}
            if name in existing:
                return

            try:
                await client.post(
                    urls.qemu_firewall_ipset(node, vmid),
                    data={"name": name},
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to create IPSet {name} for VM {vmid}: {e}"
                ) from e

    async def get_ipset_entries(self, node: str, vmid: int, name: str) -> set[str]:
        """Retourne les CIDR actuellement présents dans un IPSet de VM.

        Args:
            node: Nœud hébergeant la VM.
            vmid: ID de la VM.
            name: Nom de l'IPSet (ex: "ipfilter-net0").

        Returns:
            Ensemble des CIDR de l'IPSet (vide si l'IPSet n'existe pas).

        Raises:
            RuntimeError: Problème API Proxmox.
        """
        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(
                    urls.qemu_firewall_ipset_entries(node, vmid, name), cache=False
                )
            except ProxmoxAPIError:
                return set()
            return {entry.get("cidr") for entry in resp.get("data", [])}

    async def sync_ipset(
        self, node: str, vmid: int, name: str, cidrs: list[str]
    ) -> None:
        """Synchronise le contenu d'un IPSet de VM avec `cidrs` (idempotent).

        Crée l'IPSet s'il n'existe pas, ajoute les entrées manquantes et
        retire celles qui ne sont plus dans `cidrs`.

        Args:
            node: Nœud hébergeant la VM.
            vmid: ID de la VM.
            name: Nom de l'IPSet (ex: "ipfilter-net0").
            cidrs: Liste des CIDR autorisés (ex: ["203.0.113.5/32"]).

        Raises:
            RuntimeError: Problème API Proxmox.
        """
        await self._ensure_ipset_exists(node, vmid, name)

        async with self._proxmox_client.get_context_manager() as client:
            try:
                resp = await client.get(
                    urls.qemu_firewall_ipset_entries(node, vmid, name), cache=False
                )
            except ProxmoxServerError as e:
                raise RuntimeError(
                    f"Failed to list entries of IPSet {name} for VM {vmid}: {e}"
                ) from e
            existing = {entry.get("cidr") for entry in resp.get("data", [])}

        wanted = set(cidrs)

        for cidr in wanted - existing:
            async with self._proxmox_client.get_context_manager() as client:
                try:
                    await client.post(
                        urls.qemu_firewall_ipset_entries(node, vmid, name),
                        data={"cidr": cidr},
                    )
                except ProxmoxServerError as e:
                    raise RuntimeError(
                        f"Failed to add {cidr} to IPSet {name} for VM {vmid}: {e}"
                    ) from e

        for cidr in existing - wanted:
            async with self._proxmox_client.get_context_manager() as client:
                try:
                    await client.delete(
                        urls.qemu_firewall_ipset_entry(node, vmid, name, cidr)
                    )
                except ProxmoxServerError as e:
                    raise RuntimeError(
                        f"Failed to remove {cidr} from IPSet {name} for VM {vmid}: {e}"
                    ) from e
