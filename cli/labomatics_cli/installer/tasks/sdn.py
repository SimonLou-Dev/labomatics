"""Tâche 2 : zone SDN VXLAN."""

from __future__ import annotations

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.tasks.base import InstallTask


class SdnTask(InstallTask):
    """Crée la zone VXLAN du cluster (pairs = IP des nœuds) et applique le SDN."""

    name = "sdn"
    label = "Zone VXLAN"
    skip_reason = "zone déjà présente"

    def is_needed(self, ctx: InstallContext) -> bool:
        """Vérifie que la zone n'existe pas déjà.

        Args:
            ctx: Contexte d'installation.

        Returns:
            False si la zone existe en VXLAN.

        Raises:
            RuntimeError: Si une zone du même nom existe avec un autre type.
        """
        assert ctx.config.vxlan is not None
        zone = ctx.config.vxlan.zone
        kind = ctx.proxmox.sdn_zone(zone)
        if kind is not None and kind != "vxlan":
            raise RuntimeError(f"La zone SDN {zone} existe déjà avec le type {kind}")
        return kind is None

    def run(self, ctx: InstallContext) -> None:
        """Crée la zone puis recharge la configuration SDN.

        Args:
            ctx: Contexte d'installation.

        Raises:
            RuntimeError: Si aucune IP de nœud n'est connue.
        """
        assert ctx.config.vxlan is not None
        vxlan = ctx.config.vxlan
        peers = [n.ip for n in ctx.proxmox.nodes() if n.ip]
        if not peers:
            raise RuntimeError(
                "Impossible de récupérer les IP des nœuds pour la zone VXLAN"
            )
        ctx.log(f"Création de la zone {vxlan.zone} (pairs : {', '.join(peers)})")
        ctx.proxmox.create_sdn_zone(vxlan.zone, peers, vxlan.mtu)
        ctx.proxmox.wait_task(ctx.proxmox.apply_sdn(), timeout=120)
        ctx.log("SDN appliqué", "ok")
