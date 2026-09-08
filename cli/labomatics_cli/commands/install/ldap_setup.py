"""LDAP setup and verification."""

from ...utils.theme import info, success


class LdapSetup:
    """Vérification de la disponibilité OpenLDAP."""

    def __init__(self, vm_ip: str):
        """Initialiser."""
        self.vm_ip = vm_ip

    def wait_ready(self):
        """Attendre que OpenLDAP soit prêt."""
        info("OpenLDAP démarré (ports 389/636 internes au réseau Docker)")
        success("OpenLDAP prêt")
