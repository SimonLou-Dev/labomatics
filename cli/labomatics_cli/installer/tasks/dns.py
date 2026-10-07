"""Tâche 5 : dnsmasq sur la VM."""

from __future__ import annotations

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.proxmox_api import ProxmoxError
from labomatics_cli.installer.tasks.base import InstallTask

CONF_TMP = "/tmp/labomatics-dnsmasq.conf"
RESOLV_TMP = "/tmp/labomatics-resolv.conf"
APPLY_SCRIPT = f"""set -e
sudo dnf install -y dnsmasq
sudo install -m 644 {CONF_TMP} /etc/dnsmasq.conf
sudo systemctl disable --now systemd-resolved || true
sudo systemctl enable dnsmasq
sudo systemctl restart dnsmasq
sudo rm -f /etc/resolv.conf
sudo install -m 644 {RESOLV_TMP} /etc/resolv.conf
"""


class DnsTask(InstallTask):
    """Configure dnsmasq sur la VM ; le fichier est réécrit à chaque passage."""

    name = "dns"
    label = "DNS sur la VM"

    def _node_entries(self, ctx: InstallContext) -> dict[str, str]:
        """Associe les noms ACME des nœuds à leur IP.

        Args:
            ctx: Contexte d'installation.

        Returns:
            Les entrées `fqdn -> ip` (vide si Proxmox ne les donne pas).
        """
        entries: dict[str, str] = {}
        try:
            for node in ctx.proxmox.nodes():
                for fqdn in ctx.proxmox.node_fqdns(node.name):
                    if node.ip:
                        entries[fqdn] = node.ip
        except ProxmoxError as exc:
            ctx.log(f"Noms des nœuds ignorés : {exc}", "warn")
        return entries

    def run(self, ctx: InstallContext) -> None:
        """Génère la configuration, l'envoie sur la VM et redémarre dnsmasq.

        Args:
            ctx: Contexte d'installation.
        """
        assert ctx.config.vm is not None
        vm = ctx.config.vm
        entries = self._node_entries(ctx)
        ctx.store.set_data("node_dns_entries", entries)
        conf = ctx.templates.render(
            "dns/dnsmasq.conf.j2",
            domain=vm.domain,
            vm_ip=vm.vm_ip,
            upstream=vm.dns_upstream,
            node_entries=entries,
        )
        ssh = ctx.vm_ssh
        ssh.put_text(CONF_TMP, conf)
        ssh.put_text(RESOLV_TMP, f"nameserver 127.0.0.1\nsearch {vm.domain}\n")
        ssh.run(APPLY_SCRIPT)
        ctx.log("dnsmasq configuré", "ok")
