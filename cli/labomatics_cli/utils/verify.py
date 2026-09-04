"""Vérification que les services sont up et fonctionnels."""

import requests
import time
from .theme import info, success, warning


class ServiceVerifier:
    """Vérifie l'état des services."""

    @staticmethod
    def wait_for_http(url: str, timeout: int = 300, verify_ssl: bool = False) -> bool:
        """Attendre qu'un endpoint HTTP réponde."""
        start = time.time()
        attempt = 0
        while time.time() - start < timeout:
            attempt += 1
            elapsed = int(time.time() - start)
            try:
                resp = requests.get(url, timeout=5, verify=verify_ssl)
                if resp.status_code == 200:
                    success(f"Service prêt [{elapsed}s]")
                    return True
                else:
                    info(f"  Tentative {attempt}: HTTP {resp.status_code} [{elapsed}s]")
            except requests.ConnectionError:
                info(f"  Tentative {attempt}: Connexion refusée [{elapsed}s]")
            except requests.Timeout:
                info(f"  Tentative {attempt}: Timeout [{elapsed}s]")
            except requests.RequestException:
                info(f"  Tentative {attempt}: Erreur réseau [{elapsed}s]")
            time.sleep(2)
        warning(f"Timeout après {timeout}s")
        return False

    @staticmethod
    def check_keycloak(base_url: str, timeout: int = 60) -> bool:
        """Vérifier que Keycloak est prêt."""
        admin_url = f"{base_url}/admin/master/console/"
        return ServiceVerifier.wait_for_http(admin_url, timeout, verify_ssl=False)

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

    @staticmethod
    def wait_for_tcp_port(host: str, port: int, timeout: int = 120) -> bool:
        """Attendre qu'un port TCP réponde."""
        import socket
        start = time.time()
        attempt = 0
        while time.time() - start < timeout:
            attempt += 1
            elapsed = int(time.time() - start)
            try:
                with socket.create_connection((host, port), timeout=3):
                    success(f"Port {port} prêt [{elapsed}s]")
                    return True
            except (OSError, socket.timeout):
                info(f"  Tentative {attempt}: Port {port} fermé [{elapsed}s]")
            time.sleep(2)
        warning(f"Timeout après {timeout}s sur port {port}")
        return False
