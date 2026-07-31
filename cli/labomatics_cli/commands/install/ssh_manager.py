"""SSH management - connections, file operations, key generation."""

import subprocess
from pathlib import Path

from ...utils.ssh import SSHClient
from ...utils.theme import info, success, warning
from rich.prompt import Prompt


class SSHManager:
    """Gestion SSH centralisée."""

    @staticmethod
    def get_or_generate_cli_key() -> tuple[str, str]:
        """Récupérer ou générer la clé SSH du CLI.

        Returns:
            (ssh_privkey_path, ssh_pubkey_content)
        """
        ssh_key_path = Path.home() / ".ssh" / "labomatics-cli"
        ssh_pubkey_path = Path(f"{ssh_key_path}.pub")

        if ssh_key_path.exists():
            info(f"Clé CLI existante: {ssh_key_path}")
            cli_ssh_key = ssh_pubkey_path.read_text().strip()
            return str(ssh_key_path), cli_ssh_key

        info("Génération clé SSH labomatics-cli...")
        ssh_key_path.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                str(ssh_key_path),
                "-N",
                "",
                "-C",
                "labomatics-cli",
            ],
            check=True,
        )

        cli_ssh_key = ssh_pubkey_path.read_text().strip()
        success(f"Clé CLI générée: {ssh_key_path}")
        ssh_key_path.chmod(0o600)

        return str(ssh_key_path), cli_ssh_key

    @staticmethod
    def collect_ssh_keys() -> str:
        """Collecter les clés SSH de l'utilisateur."""
        ssh_keys_list = []

        # Demander la clé SSH publique du client
        from ...utils.theme import console

        console.print("\n[cyan]Clés SSH à ajouter à labomatics:[/cyan]")
        client_ssh_key = Prompt.ask(
            "  Clé SSH publique du client (optionnel)", default=""
        )
        if client_ssh_key.strip():
            ssh_keys_list.append(client_ssh_key.strip())

        # Ajouter la clé CLI
        _, cli_ssh_key = SSHManager.get_or_generate_cli_key()
        ssh_keys_list.append(cli_ssh_key)

        return "\n".join(ssh_keys_list)

    @staticmethod
    def connect_to_host(
        host: str, user: str = "root", password: str = None, key_filename: str = None
    ) -> SSHClient:
        """Connecter à un hôte SSH."""
        ssh = SSHClient(host, user=user, password=password, key_filename=key_filename)
        ssh.connect()
        return ssh

    @staticmethod
    def connect_to_proxmox_node(node_ip: str, node_user: str = "root") -> SSHClient:
        """Connecter à un nœud Proxmox."""
        node_password = Prompt.ask(f"    Password [{node_ip}]", password=True)
        ssh = SSHClient(node_ip, user=node_user, password=node_password)
        ssh.connect()
        return ssh

    @staticmethod
    def propagate_ca_certificate(
        ca_cert_content: str, node_ips: dict[str, str], node_user: str = "root"
    ) -> None:
        """Propager le certificat CA à tous les nœuds."""

        info("Propagation certificat CA sur tous les nœuds...")
        for node_name, node_ip in node_ips.items():
            try:
                node_ssh = SSHManager.connect_to_proxmox_node(node_ip, node_user)
                node_ssh.exec_command("mkdir -p /usr/local/share/ca-certificates")
                node_ssh.put_file_content(
                    "/usr/local/share/ca-certificates/labomatics-ca.crt",
                    ca_cert_content,
                )
                node_ssh.exec_command("update-ca-certificates")
                node_ssh.disconnect()
                success(f"  ✓ {node_name}")
            except Exception as e:
                warning(f"  ✗ {node_name}: {e}")

    @staticmethod
    def upload_cloud_init(
        ssh: SSHClient, domain: str, vm_wan_ip: str, kc_password: str
    ) -> None:
        """Uploader et configurer cloud-init."""
        from ...templates import render_template

        info("Upload configuration cloud-init...")
        userdata = render_template(
            "cloud-init.yml",
            {
                "DOMAIN": domain,
                "KEYCLOAK_ADMIN_PASSWORD": kc_password,
                "VM_WAN_IP": vm_wan_ip,
            },
        )
        ssh.put_file_content("/etc/labomatics/cloud-init.yml", userdata)
        success("Cloud-init uploadé")

    @staticmethod
    def upload_docker_compose(ssh: SSHClient, domain: str) -> None:
        """Uploader la configuration Docker Compose."""
        from ...templates import render_template

        info("Upload docker-compose.yml...")
        docker_config = render_template("docker-compose.yml", {"DOMAIN": domain})
        ssh.exec_command("mkdir -p /etc/labomatics")
        ssh.put_file_content("/etc/labomatics/docker-compose.yml", docker_config)
        success("docker-compose.yml uploadé")

    @staticmethod
    def start_docker_services(ssh: SSHClient) -> None:
        """Démarrer les services Docker."""
        info("Démarrage des services Docker...")
        stdout, stderr, rc = ssh.exec_command(
            "cd /etc/labomatics && sudo docker compose up -d"
        )
        if rc != 0:
            raise RuntimeError(f"docker compose failed: {stderr}")
        success("Services démarrés")

    @staticmethod
    def get_node_credentials() -> str:
        """Demander le user pour les nœuds Proxmox."""
        from ...utils.theme import console

        console.print("\n[cyan]Accès aux nœuds Proxmox pour certificat CA:[/cyan]")
        node_user = Prompt.ask("  User Proxmox", default="root")
        return node_user
