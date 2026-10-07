import asyncio

from labomatics_cli.tui import (
    ConfirmField,
    ListField,
    PasswordField,
    RadioField,
    SelectField,
    Step,
    SummarySection,
    TextField,
    Wizard,
    WizardContext,
)
from labomatics_cli.tui import validators as v
from tui_harness import (
    CTRL_C,
    CTRL_U,
    DELETE,
    DOWN,
    ENTER,
    RIGHT,
    STAB,
    TAB,
    UP,
    WaitUntil,
    check,
    find_chars,
    focused,
    on_screen,
    run,
    screen_lines,
)


def test_dynamic_visible_cross_field_factory_and_saved_hook():
    """Options dynamiques, champ/étape conditionnels, IpIn, fabrique d'étape et hook de sauvegarde."""
    saved = []
    ctx = WizardContext(data={"bridges": ["vmbr0", "vmbr1"]})

    mode = RadioField("Mode", ["NAT", "Bridge"], key="net.mode")
    bridge = SelectField(
        "Bridge",
        lambda c: c.data["bridges"],
        key="net.bridge",
        visible_if=lambda c: c.values["net.mode"] == "Bridge",
    )
    cidr = TextField("Réseau", key="net.cidr", validator=v.Cidr())
    gateway = TextField("Passerelle", key="net.gw", validator=v.IpIn("net.cidr"))

    async def discover(c):
        """Simule la découverte des nœuds."""
        c.data["nodes"] = ["pve1", "pve2"]
        return None

    def passwords(c):
        """Fabrique un champ mot de passe par nœud."""
        return [
            PasswordField(f"Mot de passe {n}", key=f"pw.{n}", required=True)
            for n in c.data["nodes"]
        ]

    builds = []
    factory = Step("Nœuds", lambda c: builds.append(1) or passwords(c))
    bridge_only = Step(
        "Bridge seul",
        [TextField("Note", key="note")],
        visible_if=lambda c: c.values["net.mode"] == "Bridge",
    )
    steps = [
        Step("Réseau", [mode, bridge, cidr, gateway], on_submit=discover),
        factory,
        bridge_only,
    ]
    w = Wizard(
        "T", steps, context=ctx, on_step_saved=lambda s, c: saved.append(s.title)
    )

    def pw(name):
        """Champ mot de passe d'un nœud."""
        return w.steps[1].fields[name]

    feed = [
        check(
            lambda: not bridge.visible
            and w.ctx.values == {"net.mode": "NAT", "net.cidr": "", "net.gw": ""},
            "bridge caché",
        ),
        RIGHT,
        check(
            lambda: bridge.visible
            and "net.bridge" in w.ctx.values
            and bridge.value == "vmbr0",
            "bridge visible",
        ),
        TAB,
        check(lambda: focused(w, bridge), "focus select"),
        ENTER,
        DOWN,
        ENTER,
        check(lambda: bridge.value == "vmbr1", "vmbr1"),
        TAB,
        "10.0.0.0/24",
        TAB,
        "10.0.0.255",
        TAB,
        check(
            lambda: gateway.error and "broadcast" in gateway.error,
            f"bord refusé : {gateway.error}",
        ),
        STAB,
        CTRL_U,
        "10.0.0.1",
        TAB,
        ENTER,
        WaitUntil(lambda: w.index == 1),
        check(
            lambda: saved == ["Réseau"] and len(w.steps[1].fields) == 2,
            f"étape 2 : {saved}",
        ),
        check(lambda: focused(w, w.steps[1].fields[0]), "focus premier champ fabriqué"),
        "a",
        TAB,
        "b",
        TAB,
        TAB,
        ENTER,
        check(
            lambda: w.index == 2 and saved == ["Réseau", "Nœuds"],
            "étape conditionnelle visible",
        ),
        check(lambda: on_screen(w, "Étape 3/4 — Bridge seul"), "numérotation"),
        TAB,
        TAB,
        ENTER,
        check(
            lambda: w.recap_step is w.current and saved[-1] == "Bridge seul", "récap"
        ),
        check(
            lambda: on_screen(w, "Étape 4/4")
            and on_screen(w, "vmbr1")
            and on_screen(w, "••••••••"),
            "récap rendu",
        ),
        TAB,
        TAB,
        ENTER,
    ]
    result, _ = run(w, feed)
    assert (
        result["net.bridge"] == "vmbr1"
        and result["pw.pve1"] == "a"
        and result["pw.pve2"] == "b"
    )
    assert result["net.gw"] == "10.0.0.1" and "note" in result
    assert saved == ["Réseau", "Nœuds", "Bridge seul"], saved


def test_factory_carries_values_on_rebuild():
    """Revenir sur une étape fabriquée la reconstruit en gardant les valeurs."""
    built = []
    factory = Step("Nœuds", lambda c: built.append(1) or [TextField("Mdp", key="pw")])
    w = Wizard(
        "T",
        [Step("A", [ConfirmField("Avancé", key="adv", default=False)]), factory],
        recap=False,
    )
    feed = [
        TAB,
        ENTER,
        "secret",
        TAB,
        ENTER,
        check(lambda: w.index == 0, "retour"),
        TAB,
        ENTER,
        check(
            lambda: w.index == 1
            and len(built) == 2
            and w.current.fields[0].value == "secret",
            "valeur gardée",
        ),
        TAB,
        TAB,
        ENTER,
    ]
    result, _ = run(w, feed)
    assert result == {"adv": False, "pw": "secret"}


def test_hidden_step_is_skipped():
    """Une étape invisible est sautée par la navigation et la numérotation."""
    hidden = Step(
        "Avancé", [TextField("X", key="x")], visible_if=lambda c: c.values["adv"]
    )
    w = Wizard(
        "T",
        [
            Step("A", [ConfirmField("Avancé", key="adv", default=False)]),
            hidden,
            Step("C", []),
        ],
        recap=False,
    )
    feed = [
        TAB,
        ENTER,
        check(
            lambda: w.index == 2 and on_screen(w, "Étape 2/2 — C"),
            "étape cachée sautée",
        ),
        ENTER,
    ]
    result, _ = run(w, feed)
    assert result == {"adv": False}


def test_locked_fields():
    """Champs verrouillés : affichés, non focusables, inclus ; ListField accepte de nouveaux éléments."""
    locked = TextField("Domaine", key="domain", locked=True, default="lab.local")
    other = TextField("Nom", key="name")
    pw = PasswordField("Secret", key="secret", default="x")
    items = ListField(
        "Plages",
        key="ranges",
        default=["10.0.0.1"],
        locked=True,
        item_validator=v.IpOrRange(),
    )
    w = Wizard(
        "T",
        [Step("A", [locked, other, pw, items])],
        locked_keys={"secret"},
        recap=False,
    )
    feed = [
        check(
            lambda: focused(w, other)
            and locked.focus_target is None
            and pw.focus_target is None,
            "focus saute le verrou",
        ),
        check(
            lambda: on_screen(w, "lab.local") and on_screen(w, "(verrouillé)"),
            "valeur verrouillée affichée",
        ),
        check(lambda: on_screen(w, "••••••••"), "mot de passe masqué"),
        check(lambda: not find_chars(w, "✕"), "pas de croix sur l'existant"),
        "bob",
        TAB,
        check(lambda: focused(w, items), "focus liste"),
        "10.0.0.9",
        ENTER,
        check(
            lambda: items.items == ["10.0.0.1", "10.0.0.9"]
            and len(find_chars(w, "✕")) == 1,
            "ajout + une seule croix",
        ),
        TAB,
        TAB,
        check(lambda: focused(w, items.list_window), "liste focalisable"),
        DOWN,
        DELETE,
        check(lambda: items.items == ["10.0.0.1"], "nouvel élément retiré"),
        UP,
        DELETE,
        check(lambda: items.items == ["10.0.0.1"], "élément verrouillé conservé"),
        TAB,
        TAB,
        ENTER,
    ]
    result, _ = run(w, feed)
    assert result == {
        "domain": "lab.local",
        "name": "bob",
        "secret": "x",
        "ranges": ["10.0.0.1"],
    }, result


def test_initial_values_and_start_step():
    """initial_values préremplit, start_step reprend à la bonne étape (et est borné)."""
    steps = [
        Step("A", [TextField("A", key="a")]),
        Step("B", [TextField("B", key="b", default="défaut")]),
    ]
    w = Wizard(
        "T", steps, initial_values={"a": "1", "b": "2"}, start_step=1, recap=False
    )
    result, _ = run(
        w,
        [
            check(lambda: w.index == 1 and on_screen(w, "Étape 2/2"), "reprise"),
            ENTER,
            TAB,
            ENTER,
        ],
    )
    assert result == {"a": "1", "b": "2"}
    w = Wizard("T", steps, start_step=99, recap=False)
    assert w.index == 1


def test_on_step_saved_error_path():
    """Une exception du hook s'affiche, reste sur l'étape, puis un nouvel essai passe."""
    calls = []

    def hook(step, ctx):
        """Hook qui échoue au premier appel."""
        calls.append(step.title)
        if len(calls) == 1:
            raise RuntimeError("disque plein")

    w = Wizard(
        "T",
        [Step("A", [TextField("A", key="a", default="x")]), Step("B", [])],
        on_step_saved=hook,
        recap=False,
    )
    feed = [
        TAB,
        ENTER,
        check(
            lambda: w.index == 0
            and w.step_error == "disque plein"
            and on_screen(w, "✗ disque plein"),
            "erreur du hook",
        ),
        ENTER,
        check(lambda: w.index == 1 and calls == ["A", "A"], f"réessai : {calls}"),
        ENTER,
    ]
    result, _ = run(w, feed)
    assert result == {"a": "x"} and calls == ["A", "A", "B"]


def test_on_submit_error_and_exception():
    """on_submit : erreur retournée, exception, spinner et saisie ignorée."""
    state = {"n": 0}

    async def submit(ctx):
        """Soumission qui refuse puis lève une exception."""
        state["n"] += 1
        await asyncio.sleep(0.3)
        if state["n"] == 1:
            return "refusé"
        if state["n"] == 2:
            raise ValueError("jeton expiré")
        return None

    w = Wizard(
        "T",
        [Step("A", [TextField("A", key="a", default="x")], on_submit=submit)],
        recap=False,
    )
    feed = [
        TAB,
        ENTER,
        check(lambda: w.loading and on_screen(w, "Vérification…"), "spinner"),
        "zzz",
        WaitUntil(lambda: not w.loading),
        check(
            lambda: w.step_error == "refusé" and w.steps[0].fields[0].value == "x",
            "erreur",
        ),
        ENTER,
        WaitUntil(lambda: not w.loading),
        check(lambda: w.step_error == "jeton expiré", "exception"),
        ENTER,
    ]
    result, _ = run(w, feed)
    assert result == {"a": "x"}


def test_install_done_skip_step_and_success():
    """Écran d'installation : mark_done, skip, step, barre sans pourcentage, retour des valeurs."""

    async def install(values, ui):
        """Simule une installation."""
        ui.mark_done("Préparation")
        ui.skip("Réseau", "déjà configuré")
        ui.step("Templates")
        ui.log("copie", "ok")
        ui.log("attention", "warn")
        await asyncio.sleep(0.2)
        ui.step(3)
        await asyncio.sleep(0.1)

    w = Wizard(
        "T",
        [Step("A", [TextField("A", key="a", default="x")])],
        install_steps=["Préparation", "Réseau", "Templates", "Vérifications"],
        on_install=install,
        recap=False,
    )
    feed = [
        TAB,
        ENTER,
        check(lambda: w.mode == "install", "installation"),
        WaitUntil(lambda: w.install.done, 15),
        check(
            lambda: w.reporter.status == ["done", "skipped", "done", "done"],
            str(w.reporter.status),
        ),
        check(
            lambda: on_screen(w, "Réseau : ignoré (déjà configuré)")
            and on_screen(w, "Tout est prêt ✓"),
            "logs",
        ),
        check(
            lambda: on_screen(w, "Installation terminée — 4/4 étapes")
            and not any("%" in row for row in screen_lines(w)),
            "libellé",
        ),
        check(
            lambda: find_chars(w, "░") and focused(w, w.install.quit_btn),
            "segment ignoré + Quitter",
        ),
        ENTER,
    ]
    result, rendered = run(w, feed)
    assert result == {"a": "x"}
    assert "38;2;255;107;53" in rendered


def test_install_success_shows_summary_and_warnings():
    """Succès avec récapitulatif : sections alignées et avertissements, journal masqué."""

    async def install(values, ui):
        """Simule une installation qui prépare un récapitulatif."""
        ui.step("Un")
        ui.log("détail technique", "ok")
        ui.log("ajoute une entrée hosts", "warn")
        ui.summary = [
            SummarySection("Accès", [("Application", "https://app.lab.fr")]),
            SummarySection("Compte", [("Identifiant", "jean")], "À changer."),
        ]

    w = Wizard(
        "T", [Step("A", [])], install_steps=["Un"], on_install=install, recap=False
    )
    feed = [
        ENTER,
        WaitUntil(lambda: w.install.done),
        check(
            lambda: on_screen(w, "Application   https://app.lab.fr")
            and on_screen(w, "Identifiant   jean")
            and on_screen(w, "Accès")
            and on_screen(w, "À changer.")
            and on_screen(w, "À vérifier")
            and on_screen(w, "! ajoute une entrée hosts"),
            "récapitulatif",
        ),
        check(lambda: not on_screen(w, "détail technique"), "journal masqué"),
        ENTER,
    ]
    run(w, feed)


def test_install_long_log_line_does_not_shift_the_log():
    """Une dernière ligne plus large que l'écran ne décale pas le journal à gauche."""

    async def install(values, ui):
        """Simule une installation qui échoue sur un message très long."""
        ui.step("Un")
        ui.log("première ligne", "ok")
        raise RuntimeError("Disque plein " + "x" * 300)

    w = Wizard(
        "T", [Step("A", [])], install_steps=["Un"], on_install=install, recap=False
    )
    feed = [
        ENTER,
        WaitUntil(lambda: w.install.done),
        check(
            lambda: on_screen(w, "✓ première ligne") and on_screen(w, "✗ Disque plein"),
            "début des lignes visible",
        ),
        ENTER,
    ]
    run(w, feed)


def test_install_failure():
    """Échec : segment rouge, libellé d'échec, Quitter renvoie None."""

    async def install(values, ui):
        """Simule une installation."""
        ui.step("Un")
        ui.step("Deux")
        raise RuntimeError("Disque plein")

    w = Wizard(
        "T",
        [Step("A", [])],
        install_steps=["Un", "Deux"],
        on_install=install,
        recap=False,
    )
    feed = [
        ENTER,
        WaitUntil(lambda: w.install.done),
        check(
            lambda: w.reporter.failed and w.reporter.status == ["done", "failed"],
            str(w.reporter.status),
        ),
        check(
            lambda: on_screen(w, "Échec à l'étape 2/2 — Deux")
            and on_screen(w, "Disque plein"),
            "libellé",
        ),
        ENTER,
    ]
    result, _ = run(w, feed)
    assert result is None


def test_small_terminal_and_ctrl_c():
    """Un terminal de 16 lignes ne plante pas ; Ctrl+C renvoie None."""
    fields = [TextField(f"Champ {i}", key=f"f{i}") for i in range(8)]
    w = Wizard("T", [Step("A", fields)])
    seen = {}

    def record():
        """Mémorise l'état de l'écran."""
        lines = screen_lines(w)
        seen["title"] = any("T" == row.strip() for row in lines[:3])
        seen["help"] = "Ctrl+C quitter" in lines[-1]

    result, _ = run(w, [record, CTRL_C], rows=16)
    assert result is None and seen == {"title": True, "help": True}
