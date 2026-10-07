"""Tâche 13 : contrôle de santé et données de l'écran final."""

from __future__ import annotations

import socket
import time
from typing import Any, Callable, Optional

import requests

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.keycloak_api import REALM
from labomatics_cli.installer.tasks.base import InstallTask

HTTP_ATTEMPTS = 30
HTTP_DELAY = 5.0
PUBLIC_HOSTS = ("keycloak", "labomatics", "api.labomatics", "traefik")


def resolve_locally(name: str) -> list[str]:
    """Résout un nom en IPv4 avec le résolveur du poste (fichier hosts compris).

    Args:
        name: Nom à résoudre.

    Returns:
        Les adresses trouvées, liste vide si le nom est inconnu.
    """
    try:
        infos = socket.getaddrinfo(name, None, socket.AF_INET)
    except socket.gaierror:
        return []
    return sorted({str(info[4][0]) for info in infos})


class HealthTask(InstallTask):
    """Vérifie l'API, la découverte OIDC et le realm Proxmox, puis affiche l'accès.

    La résolution des noms depuis le poste n'est qu'un avertissement : elle dépend
    du DNS de l'utilisateur, pas de l'installation.
    """

    name = "health"
    label = "Contrôle de santé"
    recorded = False

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        resolver: Callable[[str], list[str]] = resolve_locally,
        delay: float = HTTP_DELAY,
    ) -> None:
        """Initialise la tâche.

        Args:
            session: Session HTTP, remplaçable en test.
            resolver: Résolution d'un nom en IPv4, remplaçable en test.
            delay: Pause entre deux tentatives HTTP en secondes.
        """
        self.session = session or requests.Session()
        self.session.verify = False
        self.resolver = resolver
        self.delay = delay

    def run(self, ctx: InstallContext) -> None:
        """Exécute les contrôles ; l'échec de l'un d'eux fait échouer la tâche.

        Args:
            ctx: Contexte d'installation.

        Raises:
            RuntimeError: Avec la liste des contrôles en échec.
        """
        failures = []
        for label, check in (
            ("API /health", self._api),
            ("Découverte OIDC Keycloak", self._discovery),
            ("Realm OIDC Proxmox", self._proxmox_realm),
        ):
            try:
                check(ctx)
            except Exception as exc:
                failures.append(f"{label} : {exc}")
                ctx.log(f"{label} : {exc}", "error")
            else:
                ctx.log(label, "ok")
        self._local_dns(ctx)
        if failures:
            raise RuntimeError("; ".join(failures))
        self._summary(ctx)

    def _get(self, ctx: InstallContext, host: str, path: str) -> requests.Response:
        """Interroge Traefik sur la VM avec le bon nom d'hôte, avec plusieurs tentatives.

        Args:
            ctx: Contexte d'installation.
            host: Nom d'hôte demandé (routage Traefik).
            path: Chemin de la requête.

        Returns:
            La première réponse 200.

        Raises:
            RuntimeError: Si aucune tentative n'aboutit.
        """
        assert ctx.config.vm is not None
        last = "aucune réponse"
        for attempt in range(HTTP_ATTEMPTS):
            try:
                response = self.session.get(
                    f"https://{ctx.config.vm.vm_ip}{path}",
                    headers={"Host": host},
                    timeout=10,
                )
                if response.status_code == 200:
                    return response
                last = f"HTTP {response.status_code}"
            except requests.RequestException as exc:
                last = str(exc)
            if attempt < HTTP_ATTEMPTS - 1:
                time.sleep(self.delay)
        raise RuntimeError(last)

    def _api(self, ctx: InstallContext) -> None:
        """Vérifie `/health` de l'API.

        Args:
            ctx: Contexte d'installation.
        """
        assert ctx.config.vm is not None
        self._get(ctx, f"api.labomatics.{ctx.config.vm.domain}", "/health")

    def _discovery(self, ctx: InstallContext) -> None:
        """Vérifie la découverte OIDC du realm et son émetteur.

        Args:
            ctx: Contexte d'installation.

        Raises:
            RuntimeError: Si l'émetteur annoncé n'est pas celui attendu.
        """
        assert ctx.config.vm is not None
        host = f"keycloak.{ctx.config.vm.domain}"
        data: dict[str, Any] = self._get(
            ctx, host, f"/realms/{REALM}/.well-known/openid-configuration"
        ).json()
        expected = f"https://{host}/realms/{REALM}"
        if data.get("issuer") != expected:
            raise RuntimeError(f"émetteur {data.get('issuer')} au lieu de {expected}")

    def _proxmox_realm(self, ctx: InstallContext) -> None:
        """Vérifie que le realm OIDC existe côté Proxmox.

        Args:
            ctx: Contexte d'installation.

        Raises:
            RuntimeError: Si le realm est absent.
        """
        if not ctx.proxmox.realm_exists(REALM):
            raise RuntimeError(f"realm {REALM} absent de Proxmox")

    def _local_dns(self, ctx: InstallContext) -> None:
        """Vérifie que le poste résout les noms publics vers la VM, sinon explique quoi faire.

        Args:
            ctx: Contexte d'installation.
        """
        assert ctx.config.vm is not None
        vm = ctx.config.vm
        names = [f"{host}.{vm.domain}" for host in PUBLIC_HOSTS]
        wrong = [name for name in names if vm.vm_ip not in self.resolver(name)]
        if not wrong:
            ctx.log("Résolution DNS depuis ce poste", "ok")
            return
        ctx.log(f"Ce poste ne résout pas vers {vm.vm_ip} : {', '.join(wrong)}", "warn")
        ctx.log(
            f"Ajoute une zone {vm.domain} pointant vers {vm.vm_ip} dans ton DNS "
            f"(le DNS de la VM répond sur {vm.vm_ip}:53), ou dans le fichier hosts :",
            "warn",
        )
        ctx.log(f"{vm.vm_ip} {' '.join(names)}", "warn")

    def _summary(self, ctx: InstallContext) -> None:
        """Enregistre les URLs et l'accès administrateur pour l'écran final.

        Args:
            ctx: Contexte d'installation.
        """
        assert ctx.config.vm is not None and ctx.config.admin is not None
        domain = ctx.config.vm.domain
        summary = {
            "frontend_url": f"https://labomatics.{domain}",
            "api_url": f"https://api.labomatics.{domain}",
            "keycloak_url": f"https://keycloak.{domain}/admin/{REALM}/console/",
            "admin_username": ctx.config.admin.username,
            "admin_temp_password": ctx.store.secrets.admin_temp_password,
        }
        ctx.store.set_data("final_summary", summary)
