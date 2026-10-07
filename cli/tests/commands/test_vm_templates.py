from labomatics_cli.commands.templates.templates import VmTemplateCatalog


def test_repo_catalog_loads_all_templates():
    """Les quatre templates du repo sont lus depuis `templates/vm/`."""
    names = {t.name for t in VmTemplateCatalog().load()}
    assert names == {"alpine-3-24", "debian-trixie", "fedora-44", "ubuntu-resolute"}


def test_catalog_reads_custom_root(tmp_path):
    """Un dossier personnalisé est lu à la place de celui du repo."""
    (tmp_path / "vm").mkdir()
    (tmp_path / "vm" / "x.yaml").write_text(
        "name: x\nvmid: 1\niso_url: u\niso_filename: f\nmemory: 512\ndisk_size: 1G\n"
    )
    assert [t.name for t in VmTemplateCatalog(tmp_path).load()] == ["x"]


def test_catalog_missing_folder_is_empty(tmp_path):
    """Sans dossier `vm/`, le catalogue est vide."""
    assert VmTemplateCatalog(tmp_path).load() == []
