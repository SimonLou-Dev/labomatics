"""Tâche 13 : contrôle de santé et données de l'écran final."""

from __future__ import annotations

import time
from typing import Any, Optional

import requests

from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.dns_probe import DnsProbe
from labomatics_cli.installer.keycloak_api import REALM
from labomatics_cli.installer.tasks.base import InstallTask

HTTP_ATTEMPTS = 30
HTTP_DELAY = 5.0


class HealthTask(InstallTask):
    """Vérifie l'API, la découverte OIDC, le realm Proxmox et le DNS, puis affiche l'accès."""

    name = "health"
    label = "Contrôle de santé"
    recorded = False

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        dns: Optional[DnsProbe] = None,
        delay: float = HTTP_DELAY,
    ) -> None:
        """Initialise la tâche.

        Args:
            session: Session HTTP, remplaçable en test.
            dns: Sonde DNS, remplaçable en test.
            delay: Pause entre deux tentatives HTTP en secondes.
        """
        self.session = session or requests.Session()
        self.session.verify = False
        self.dns = dns or DnsProbe()
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
            ("Résolution DNS", self._dns),
        ):
            try:
                check(ctx)
            except Exception as exc:
                failures.append(f"{label} : {exc}")
                ctx.log(f"{label} : {exc}", "error")
            else:
                ctx.log(label, "ok")
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

    def _dns(self, ctx: InstallContext) -> None:
        """Vérifie que le DNS de la VM résout le domaine vers la VM.

        Args:
            ctx: Contexte d'installation.

        Raises:
            RuntimeError: Si la réponse ne contient pas l'IP de la VM.
        """
        assert ctx.config.vm is not None
        vm = ctx.config.vm
        name = f"keycloak.{vm.domain}"
        try:
            found = self.dns.resolve(vm.vm_ip, name)
        except OSError as exc:
            raise RuntimeError(f"{vm.vm_ip} ne répond pas ({exc})") from exc
        if vm.vm_ip not in found:
            raise RuntimeError(f"{name} résolu en {found or 'rien'}")

    def _summary(self, ctx: InstallContext) -> None:
        """Consigne les URLs et l'accès administrateur pour l'écran final.

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
        ctx.log(f"Application : {summary['frontend_url']}", "ok")
        ctx.log(f"API : {summary['api_url']}", "ok")
        ctx.log(f"Keycloak : {summary['keycloak_url']}", "ok")
        ctx.log(f"Identifiant : {summary['admin_username']}", "ok")
        ctx.log(
            f"Mot de passe temporaire : {summary['admin_temp_password']} "
            "(à changer à la première connexion)",
            "warn",
        )
