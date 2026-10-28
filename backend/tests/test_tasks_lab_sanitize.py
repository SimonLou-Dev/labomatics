"""Sanitisation du username teacher/admin pour Proxmox — issue #58.

Le nom de la VM routeur (`router-{user_name}`) doit être un nom DNS valide
pour Proxmox. L'ancienne sanitisation remplaçait les caractères invalides
par un underscore (lui-même invalide pour un nom DNS Proxmox) et ne
préservait pas les points, cassant la création de lab dès que le username
Keycloak contenait un point (ex: "simon.admin" -> "simon_admin" rejeté par
Proxmox avec "value does not look like a valid DNS name").
"""

from __future__ import annotations

from labomatics.tasks.lab import sanitize_owner_username_for_proxmox


def test_dot_in_username_is_preserved_not_replaced():
    assert sanitize_owner_username_for_proxmox("simon.admin") == "simon.admin"


def test_invalid_characters_become_hyphens_not_underscores():
    result = sanitize_owner_username_for_proxmox("simon admin@test")
    assert "_" not in result
    assert result == "simon-admin-test"


def test_result_never_starts_or_ends_with_separator():
    result = sanitize_owner_username_for_proxmox("@simon.admin.")
    assert not result.startswith(("-", "."))
    assert not result.endswith(("-", "."))


def test_truncates_to_sixteen_characters():
    result = sanitize_owner_username_for_proxmox("a" * 50)
    assert len(result) <= 16
