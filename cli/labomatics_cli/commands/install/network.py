"""Network setup (DNS, dnsmasq, Traefik)."""

from ...utils.proxmox import ProxmoxClient
from ...utils.state import InstallState
from ...templates import render_template
from ...utils.theme import info, success, warning

from .helpers import allocate_first_wan_ip
from .ssh_manager import SSHManager


class NetworkSetup:
    """Configuration réseau."""

    def __init__(
        self,
        pve: ProxmoxClient,
        domain: str,
        vm_ip: str,
        ssh_key: str,
        state: InstallState,
    ):
        """Initialiser."""
        self.pve = pve
        self.domain = domain
        self.vm_ip = vm_ip
        self.state = state
        info(f"Connexion SSH à {vm_ip} (user: labomatics, key: {ssh_key})")
        self.ssh = SSHManager.connect_to_host(
            vm_ip, user="labomatics", key_filename=ssh_key
        )

    def setup_all(
        self, wan_config: dict, vxlan_config: dict, dns_servers: str, node: str
    ):
        """Configurer tout le réseau."""
        try:
            # Setup SDN
            self._setup_sdn(node, vxlan_config)

            # Collect node FQDNs
            node_dns_entries = self._collect_node_fqdns()
            self.state.set("node_dns_entries", node_dns_entries)

            # Setup infrastructure on VM
            vm_wan_ip = allocate_first_wan_ip(wan_config)
            self._setup_dnsmasq(vm_wan_ip, dns_servers, node_dns_entries)
            self._setup_traefik()
            self._setup_proxmox_dns(node)
            self._setup_vm_dns()

            # Setup certificates
            self._setup_certificates(node)

            # Start Docker
            SSHManager.start_docker_services(self.ssh)
        finally:
            self.ssh.disconnect()

    def _setup_sdn(self, node, vxlan_config):
        """Configurer SDN (zones et vnets)."""
        from rich.prompt import Confirm

        info("Configuration SDN...")
        zone_name = "labs"

        # Check if zone already exists
        if self.pve.sdn_zone_exists(zone_name):
            info(f"Zone VXLAN existante: {zone_name}")
            success("Zone SDN trouvée")
        else:
            # Collect node IPs for VXLAN peers
            all_nodes = self.pve.get_nodes()
            peers = []
            for n in all_nodes:
                n_ip = self.pve.get_node_ip(n)
                if n_ip:
                    peers.append(n_ip)

            # Show instructions to user
            from ...utils.theme import console

            console.print("\n[bold cyan]Configuration Zone VXLAN[/bold cyan]")
            console.print(f"  Zone: [yellow]{zone_name}[/yellow]")
            console.print("  Type: [yellow]vxlan[/yellow]")
            console.print(f"  Peers: [yellow]{','.join(peers)}[/yellow]")
            console.print("  MTU: [yellow]1350[/yellow]")
            console.print("\nCreer la zone manuellement dans Proxmox:")
            console.print("  1. Aller à Datacenter > SDN > Zones")
            console.print("  2. Cliquer 'Create'")
            console.print("  3. Remplir les paramètres ci-dessus")
            console.print("  4. Cliquer 'Create'\n")

            if not Confirm.ask("Zone VXLAN créée dans Proxmox?", default=False):
                raise RuntimeError("Zone VXLAN non créée - installation annulée")

            success("Zone VXLAN confirmée")

        # Apply SDN configuration
        info("Application configuration SDN...")
        try:
            self.pve.apply_sdn()
            success("SDN appliquée (tâche lancée en arrière-plan)")
        except Exception as e:
            warning(f"Application SDN: {e}")

    def _collect_node_fqdns(self) -> dict[str, str]:
        """Collecter les FQDNs des nœuds."""
        info("Récupération FQDNs nœuds...")
        entries = {}
        try:
            nodes = self.pve.get_nodes()
            info(f"  {len(nodes)} nœuds trouvés")
            for node in nodes:
                fqdns = self.pve.get_node_fqdns(node)
                node_ip = self.pve.get_node_ip(node)
                info(f"  {node}: {fqdns or 'N/A'} -> {node_ip or 'N/A'}")
                if fqdns and node_ip:
                    for fqdn in fqdns:
                        entries[fqdn] = node_ip
            info(f"  Total: {len(entries)} entrées DNS")
        except Exception as e:
            warning(f"FQDNs (optionnel): {e}")
        return entries

    def _setup_dnsmasq(self, vm_wan_ip: str, dns_servers: str, node_dns_entries: dict):
        """Configurer dnsmasq."""
        info("Configuration dnsmasq...")

        info("  Rendu du template...")
        dns_lines = "\n".join([f"server={dns}" for dns in dns_servers.split()])
        node_lines = "\n".join(
            [f"address=/{fqdn}/{ip}" for fqdn, ip in node_dns_entries.items()]
        )

        config = render_template(
            "dnsmasq.conf",
            {
                "DOMAIN": self.domain,
                "VM_WAN_IP": vm_wan_ip,
                "DNS_SERVERS": dns_lines,
                "NODE_DNS_ENTRIES": node_lines,
            },
        )
        info(f"  Template rendu ({len(config)} bytes)")

        info("  Installation + configuration dnsmasq (script unique)...")
        script = f"""
set -e
sudo dnf install -y dnsmasq
sudo mkdir -p /etc/dnsmasq.d
echo '{config}' | sudo tee /etc/dnsmasq.conf > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable dnsmasq
sudo systemctl start dnsmasq
"""
        self.ssh.exec_command(script)
        success("dnsmasq configuré")

    def _setup_traefik(self):
        """Configurer Traefik."""
        info("Configuration Traefik...")

        info("  Rendu du template...")
        config = render_template("traefik.yml", {"DOMAIN": self.domain})
        info(f"  Template rendu ({len(config)} bytes)")

        info("  Création répertoires + upload config...")
        script = f"""
set -e
mkdir -p /etc/labomatics/dynamic /etc/labomatics/logs
echo '{config}' | sudo tee /etc/labomatics/traefik.yml > /dev/null
"""
        self.ssh.exec_command(script)
        success("Traefik configuré")

    def _setup_proxmox_dns(self, node: str):
        """Configurer DNS Proxmox."""
        info("Configuration DNS Proxmox...")
        nodes = self.pve.get_nodes()
        info(f"  Configuration {len(nodes)} nœud(s) -> DNS: {self.vm_ip}")
        for n in nodes:
            try:
                info(f"    Nœud {n}...")
                self.pve.set_node_dns(n, dns1=self.vm_ip, search=self.domain)
                success(f"  DNS sur {n}")
            except Exception as e:
                warning(f"  DNS sur {n}: {e}")

    def _setup_vm_dns(self):
        """Configurer resolv.conf VM."""
        info("Configuration DNS VM...")
        resolv = f"nameserver 127.0.0.1\noptions edns0 trust-ad\nsearch {self.domain}\n"
        self.ssh.exec_command(
            f"echo '{resolv}' | sudo tee /etc/resolv.conf > /dev/null"
        )
        success("DNS VM configuré")

    def _setup_certificates(self, node):
        """Configurer certificats."""
        from .certificates import CertificateManager

        info("Configuration certificats...")
        cert_mgr = CertificateManager(self.ssh)

        # Get all nodes with IPs from /cluster/status
        node_ips = self.pve.get_nodes_with_ips()
        info(f"  Nœuds trouvés: {len(node_ips)}")
        for n, ip in node_ips.items():
            info(f"    {n}: {ip}")

        node_user = SSHManager.get_node_credentials()
        cert_mgr.generate_and_propagate(self.domain, node_ips, node_user)
        success("Certificats configurés")
