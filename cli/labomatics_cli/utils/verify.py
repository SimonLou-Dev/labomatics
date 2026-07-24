"""Vérification que les services sont up et fonctionnels."""

import requests
import time
from typing import Optional


class ServiceVerifier:
    """Vérifie l'état des services."""

    @staticmethod
    def wait_for_http(url: str, timeout: int = 300, verify_ssl: bool = False) -> bool:
        """Attendre qu'un endpoint HTTP réponde."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(url, timeout=5, verify=verify_ssl)
                if resp.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)
        return False

    @staticmethod
    def check_keycloak(base_url: str, timeout: int = 60) -> bool:
        """Vérifier que Keycloak est prêt."""
        health_url = f"{base_url}/health/ready"
        return ServiceVerifier.wait_for_http(health_url, timeout)

    @staticmethod
    def check_postgres(host: str, port: int = 5432, timeout: int = 60) -> bool:
        """Vérifier que PostgreSQL répond (via docker exec)."""
        # TODO: implement via SSH/docker exec
        time.sleep(3)  # Simple delay for now
        return True

    @staticmethod
    def check_dns(host: str, port: int = 53, timeout: int = 60) -> bool:
        """Vérifier que DNS répond (via dig/nslookup)."""
        # TODO: implement via SSH/dig
        time.sleep(2)
        return True

    @staticmethod
    def check_traefik(host: str, port: int = 8080, timeout: int = 60) -> bool:
        """Vérifier que Traefik répond."""
        url = f"http://{host}:{port}/api/overview"
        return ServiceVerifier.wait_for_http(url, timeout, verify_ssl=False)
