"""Tests unitaires pour labomatics.students."""

from pathlib import Path

import pytest

from labomatics.students import Student, load_students


# ── login() ──────────────────────────────────────────────────────────────────

def test_login_prenom_nom():
    s = Student(id=18, nom="Dupont", prenom="Jean")
    assert s.login() == "jdupont"


def test_login_uppercase():
    s = Student(id=18, nom="DUPONT", prenom="JEAN")
    assert s.login() == "jdupont"


def test_login_no_prenom():
    s = Student(id=18, nom="dupont")
    assert s.login() == "dupont"


# ── identifiants Proxmox ─────────────────────────────────────────────────────

def test_vmid():
    s = Student(id=18, nom="Dupont", prenom="Jean")
    assert s.vmid(10000) == 10018


def test_vnet_name():
    s = Student(id=18, nom="Dupont", prenom="Jean")
    assert s.vnet_name() == "vn00018"


def test_vm_name():
    s = Student(id=18, nom="Dupont", prenom="Jean")
    assert s.vm_name() == "openwrt-jdupont"


def test_vnet_alias_with_prenom():
    s = Student(id=18, nom="Dupont", prenom="Jean")
    assert s.vnet_alias() == "Jean Dupont"


def test_vnet_alias_without_prenom():
    s = Student(id=18, nom="Dupont")
    assert s.vnet_alias() == "Dupont"


def test_pool_name():
    s = Student(id=18, nom="Dupont", prenom="Jean")
    assert s.pool_name() == "jdupont"


def test_user_id():
    s = Student(id=18, nom="Dupont", prenom="Jean")
    assert s.user_id() == "jdupont@pve"


# ── load_students ─────────────────────────────────────────────────────────────

def test_load_students_basic(tmp_path):
    csv_file = tmp_path / "students.csv"
    csv_file.write_text("id,nom,prenom,flavor\n18,Dupont,Jean,CO1\n46,Michel,Marie,CO2\n")
    students = load_students(csv_file)
    assert len(students) == 2
    assert students[0].id == 18
    assert students[0].nom == "Dupont"
    assert students[0].prenom == "Jean"
    assert students[0].login() == "jdupont"
    assert students[0].flavor == "CO1"
    assert students[1].id == 46
    assert students[1].login() == "mmichel"


def test_load_students_sorted(tmp_path):
    csv_file = tmp_path / "students.csv"
    csv_file.write_text("id,nom,prenom\n46,Michel,Marie\n18,Dupont,Jean\n")
    students = load_students(csv_file)
    assert students[0].id == 18
    assert students[1].id == 46
    assert students[0].index == 1
    assert students[1].index == 2


def test_load_students_legacy_csv(tmp_path):
    """CSV sans colonnes prenom/flavor doit fonctionner (rétrocompatibilité)."""
    csv_file = tmp_path / "students.csv"
    csv_file.write_text("id,nom\n18,jdupont\n")
    students = load_students(csv_file)
    assert students[0].prenom == ""
    assert students[0].flavor == ""
    assert students[0].login() == "jdupont"


def test_load_students_empty_raises(tmp_path):
    csv_file = tmp_path / "students.csv"
    csv_file.write_text("id,nom\n")
    with pytest.raises(ValueError, match="CSV vide"):
        load_students(csv_file)


def test_load_students_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_students(tmp_path / "nonexistent.csv")
