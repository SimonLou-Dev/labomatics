"""Certificate management."""

import tempfile
from rich.prompt import Prompt

from ...utils.ssh import SSHClient
from ...utils.theme import info, success, warning


class CertificateManager:
    """Gestion des certificats TLS et CA."""

    def __init__(self, ssh: SSHClient):
        """Initialiser le manager."""
        self.ssh = ssh

    def generate_and_propagate(
        self, domain: str, node_ips: dict[str, str], node_user: str
    ) -> str:
        """Générer sur la VM et propager les certificats.

        Returns:
            Contenu du certificat CA
        """
        # Vérifier si les certificats existent
        stdout, stderr, rc = self.ssh.exec_command(
            "test -f /etc/labomatics/certs/ca.crt && echo 'exists'"
        )

        certs_exist = "exists" in stdout

        if certs_exist:
            info("CA root et certificats TLS existants (skipped)")
        else:
            info("Génération des certificats...")
            # Générer les certificats sur la VM
            self._generate_certificates(domain)

        # Récupérer le contenu du CA
        info("Récupération du CA...")
        stdout, _, _ = self.ssh.exec_command("cat /etc/labomatics/certs/ca.crt")
        ca_content = stdout
        info(f"  CA récupéré ({len(ca_content)} bytes)")

        # Propager le CA aux nœuds seulement si les certificats viennent d'être générés
        if not certs_exist and len(node_ips) > 0:
            info(f"Propagation CA aux {len(node_ips)} nœud(s)...")
            self._propagate_ca_certificate(ca_content, node_ips, node_user)
        elif certs_exist:
            info("CA existant: propagation skipped")

        return ca_content

    def _generate_certificates(self, domain: str) -> None:
        """Générer les certificats TLS sur la VM."""
        info("Génération CA root et certificats TLS...")

        info("  Génération CA root...")
        info("  Génération certificats pour 4 domaines (script unique)...")

        # Build comprehensive script (all in one SSH call)
        san_list = (
            f"DNS:{domain},DNS:*.{domain},DNS:keycloak.{domain},"
            f"DNS:api.{domain},DNS:traefik.{domain},DNS:ldap.{domain},DNS:ldap"
        )

        script = f"""
set -e
mkdir -p /etc/labomatics/certs
cd /etc/labomatics/certs

openssl genrsa -out ca.key 2048 2>/dev/null
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj '/CN=labomatics-ca' 2>/dev/null

cat > san.conf << 'SANEOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no
[req_distinguished_name]
CN = *.{domain}
[v3_req]
subjectAltName = {san_list}
SANEOF

for DOMAIN in default keycloak.{domain} api.{domain} {domain} ldap.{domain}; do
  openssl req -new -newkey rsa:2048 -nodes -config san.conf -keyout $DOMAIN.key -out $DOMAIN.csr 2>/dev/null
  openssl x509 -req -days 365 -extensions v3_req -extfile san.conf -in $DOMAIN.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out $DOMAIN.crt 2>/dev/null
done

chmod 600 *.key
rm -f *.csr *.srl san.conf
"""

        info("  Exécution script SSH...")
        self.ssh.exec_command(script)
        success("Certificats générés sur la VM")

    def _propagate_ca_certificate(
        self, ca_content: str, node_ips: dict[str, str], node_user: str
    ) -> None:
        """Propager le certificat CA sur tous les nœuds Proxmox."""
        info("Propagation certificat CA sur tous les nœuds...")

        ca_cert_content = ca_content
        if not ca_cert_content:
            raise RuntimeError("Impossible de lire le CA: contenu vide")
        info(f"  CA à propager: {len(ca_cert_content)} bytes")

        # Écrire dans un fichier temporaire
        with tempfile.NamedTemporaryFile(mode="w", suffix=".crt", delete=False) as f:
            f.write(ca_cert_content)
            temp_cert_path = f.name

        try:
            info(f"  Nœuds à configurer: {list(node_ips.keys())}")
            for node_name, node_ip in node_ips.items():
                try:
                    info(f"  Connexion SSH à {node_name} ({node_ip})...")
                    node_password = Prompt.ask(
                        f"    Password [{node_user}@{node_ip}]", password=True
                    )
                    node_ssh = SSHClient(
                        node_ip, user=node_user, password=node_password
                    )
                    node_ssh.connect(retries=3)
                    info("    Création répertoire CA...")
                    node_ssh.exec_command("mkdir -p /usr/local/share/ca-certificates")
                    info("    Upload certificat...")
                    node_ssh.put_file_content(
                        "/usr/local/share/ca-certificates/labomatics-ca.crt",
                        ca_cert_content,
                    )
                    info("    Exécution update-ca-certificates...")
                    node_ssh.exec_command("update-ca-certificates")
                    node_ssh.disconnect()
                    success(f"  ✓ {node_name}")
                except Exception as e:
                    warning(f"  ✗ {node_name}: {e}")
            success("Certificat CA propagé")
        finally:
            import os

            os.unlink(temp_cert_path)
