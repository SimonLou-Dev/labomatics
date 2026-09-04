"""Utilitaires pour LDAP."""


def domain_to_base_dn(domain: str) -> str:
    """Convertir un domaine en Base DN LDAP.

    Exemple: esgi.local -> dc=esgi,dc=local
    """
    return ",".join(f"dc={part}" for part in domain.split("."))
