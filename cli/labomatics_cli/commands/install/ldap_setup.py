"""LDAP setup and verification."""

from ...utils.verify import ServiceVerifier
from ...utils.theme import info, success


class LdapSetup:
    """Vérification de la disponibilité OpenLDAP."""

    def __init__(self, vm_ip: str):
        """Initialiser."""
        self.vm_ip = vm_ip

    def wait_ready(self):
        """Attendre que OpenLDAP (LDAPS/636) réponde."""
        info(f"Attente OpenLDAP (port 636 sur {self.vm_ip})...")
        if not ServiceVerifier.wait_for_tcp_port(self.vm_ip, 636, timeout=120):
            raise RuntimeError(
                f"Timeout: OpenLDAP (636) ne répond pas sur {self.vm_ip}"
            )
        success("OpenLDAP prêt")
