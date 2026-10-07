"""Application `labomatics install` : choix du cluster, modes et assemblage du wizard."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from rich.console import Console

from labomatics_cli.installer.checks import Checks
from labomatics_cli.installer.context import InstallContext
from labomatics_cli.installer.pages import (
    NEW_CLUSTER,
    PAGE_SECTIONS,
    AdminPage,
    AuthPage,
    ClusterChoice,
    LdapPage,
    MailPage,
    NodesPage,
    Page,
    ProxmoxPage,
    ProxyPage,
    VmPage,
    VxlanPage,
    WanPage,
)
from labomatics_cli.installer.proxmox_api import ProxmoxApi, ProxmoxError
from labomatics_cli.installer.store import InstallMode, InstallStore
from labomatics_cli.installer.runner import InstallRunner
from labomatics_cli.installer.tasks import build_tasks
from labomatics_cli.tui import InstallReporter, Step, Wizard, WizardContext

CLUSTER_NAME_KEY = "proxmox.cluster_name"


class InstallerApp:
    """Lance le wizard d'installation en mode nouveau, reprise ou édition."""

    def __init__(
        self,
        cluster: Optional[str] = None,
        *,
        base_dir: Optional[Path] = None,
        runner: Optional[InstallRunner] = None,
        api_factory: Callable[..., ProxmoxApi] = ProxmoxApi,
        checks: Optional[Checks] = None,
    ) -> None:
        """Initialise l'application.

        Args:
            cluster: Nom du cluster demandé avec `--cluster`.
            base_dir: Dossier racine des clusters (`~/.labomatics/clusters` par défaut).
            runner: Exécuteur d'installation ; les 13 tâches par défaut.
            api_factory: Construit le client Proxmox, remplaçable en test.
            checks: Contrôles réseau, remplaçables en test.
        """
        self.cluster = cluster
        self.base_dir = base_dir
        self.runner = runner or InstallRunner(build_tasks())
        self.api_factory = api_factory
        self.checks = checks or Checks()
        self.store: Optional[InstallStore] = None
        self.console = Console()
        self.proxmox_page = ProxmoxPage(api_factory, self._taken_names)
        self.pages: list[Page] = [
            self.proxmox_page,
            VmPage(self.checks, self._vm_exists),
            WanPage(),
            VxlanPage(),
            AdminPage(),
            AuthPage(),
            LdapPage(self.checks),
            ProxyPage(),
            MailPage(self.checks),
            NodesPage(self.checks),
        ]

    def run(self) -> int:
        """Choisit le cluster puis exécute le wizard.

        Returns:
            0 si le wizard est allé au bout, 1 s'il a été abandonné.
        """
        if not self._select_cluster():
            return 1
        return 0 if self.build_wizard().run() is not None else 1

    def _select_cluster(self) -> bool:
        """Détermine le cluster : option `--cluster`, choix à l'écran ou nouveau.

        Returns:
            False si l'utilisateur a abandonné le choix.
        """
        names = InstallStore.list_clusters(self.base_dir)
        name = self.cluster
        if name is None and names:
            name = ClusterChoice(names).ask()
            if name is None:
                return False
            if name == NEW_CLUSTER:
                name = None
        self.cluster = name
        if name is not None and name in names:
            self.store = InstallStore.open(name, self.base_dir)
        return True

    @property
    def mode(self) -> InstallMode:
        """Mode de lancement courant.

        Returns:
            `new` tant qu'aucun store n'est ouvert, sinon le mode du store.
        """
        return self.store.mode if self.store is not None else InstallMode.new

    def _taken_names(self) -> set[str]:
        """Noms de cluster refusés à la saisie.

        Returns:
            Les clusters existants tant qu'aucun store n'est ouvert, sinon aucun.
        """
        if self.store is not None:
            return set()
        return set(InstallStore.list_clusters(self.base_dir))

    def _vm_exists(self) -> bool:
        """Indique si la VM a déjà été créée par une installation précédente.

        Returns:
            True si la tâche `vm` est terminée.
        """
        return self.store is not None and self.store.is_task_done("vm")

    def build_wizard(self) -> Wizard:
        """Assemble le wizard selon le mode (préremplissage, verrouillage, étape de départ).

        Returns:
            Le wizard prêt à être lancé.
        """
        ctx = WizardContext()
        initial: dict = {}
        locked: set[str] = set()
        start = 0
        if self.store is None:
            if self.cluster:
                initial[CLUSTER_NAME_KEY] = self.cluster
        else:
            config = self.store.config
            initial = config.to_flat()
            locked = {CLUSTER_NAME_KEY} | (
                config.locked_keys() if self.mode == InstallMode.edit else set()
            )
            if self.mode == InstallMode.resume:
                start = self._first_unsaved()
                if start > 0 and not self._hydrate(ctx):
                    start = 0
        return Wizard(
            "LABOMATICS - CLI",
            [page.build() for page in self.pages],
            initial_values=initial,
            locked_keys=locked,
            start_step=start,
            on_step_saved=self._save,
            install_steps=self.runner.labels,
            on_install=self._install,
            context=ctx,
        )

    def _first_unsaved(self) -> int:
        """Indice de la première page non sauvegardée.

        Returns:
            L'indice, ou le nombre de pages (récapitulatif) si tout est sauvegardé.
        """
        assert self.store is not None
        config = self.store.config
        for index, page in enumerate(self.pages):
            if not page.is_saved(config):
                return index
        return len(self.pages)

    def _hydrate(self, ctx: WizardContext) -> bool:
        """Recharge le cache Proxmox quand on reprend après la première page.

        Args:
            ctx: Contexte de l'assistant.

        Returns:
            False si Proxmox est injoignable (on repart alors de la première page).
        """
        assert self.store is not None
        proxmox = self.store.config.proxmox
        if proxmox is None:
            return False
        try:
            self.proxmox_page.load(
                ctx, proxmox.url, proxmox.user, proxmox.token_id, proxmox.token_secret
            )
        except ProxmoxError as exc:
            self.console.print(f"[yellow]Reprise depuis le début : {exc}[/yellow]")
            return False
        return True

    def _save(self, step: Step, ctx: WizardContext) -> None:
        """Sauvegarde la page validée ; ouvre le store à la première page.

        Args:
            step: Étape qui vient d'être validée.
            ctx: Contexte de l'assistant.
        """
        if self.store is None:
            self.store = InstallStore.open(ctx.values[CLUSTER_NAME_KEY], self.base_dir)
            for field in step.fields:
                if field.key == CLUSTER_NAME_KEY:
                    field.locked = True
        self.store.save_page(ctx.values, PAGE_SECTIONS[step.title])

    async def _install(self, values: dict, ui: InstallReporter) -> None:
        """Construit le contexte d'installation et lance l'exécuteur.

        Args:
            values: Valeurs finales du wizard.
            ui: Rapporteur de l'écran d'installation.
        """
        assert self.store is not None
        ctx = InstallContext(
            self.store.config, self.store, ui, api_factory=self.api_factory
        )
        await self.runner.run(ctx)
