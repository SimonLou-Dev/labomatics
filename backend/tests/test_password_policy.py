"""Génération de mots de passe conformes à la `passwordPolicy` Keycloak (#85)."""

from __future__ import annotations

import string

import pytest
from keycloak.exceptions import KeycloakGetError

from labomatics.services.keycloak_service import KeycloakService
from labomatics.utils.login_helper import (
    DEFAULT_PASSWORD_LENGTH,
    DEFAULT_PASSWORD_POLICY,
    SPECIAL,
    PasswordPolicy,
    generate_password,
    parse_password_policy,
)

# Politique posée par l'installeur (cli/.../installer/tasks/keycloak.py)
INSTALLER_POLICY = (
    "length(16) and specialChars(2) and upperCase(2) and digits(2) "
    "and lowerCase(3) and passwordHistory(3) and notUsername"
)


def _assert_conforms(password: str, policy: PasswordPolicy) -> None:
    assert len(password) >= policy.length
    if policy.max_length is not None:
        assert len(password) <= policy.max_length
    assert sum(c in string.ascii_uppercase for c in password) >= policy.min_upper
    assert sum(c in string.ascii_lowercase for c in password) >= policy.min_lower
    assert sum(c in string.digits for c in password) >= policy.min_digits
    assert sum(c in SPECIAL for c in password) >= policy.min_special


# ---------------------------------------------------------------------------
# parse_password_policy
# ---------------------------------------------------------------------------


def test_parse_installer_policy() -> None:
    policy = parse_password_policy(INSTALLER_POLICY)
    assert policy == PasswordPolicy(
        length=16, min_upper=2, min_lower=3, min_digits=2, min_special=2
    )


def test_parse_stricter_policy_with_max_length() -> None:
    policy = parse_password_policy(
        "length(24) and maxLength(32) and specialChars(4) and upperCase(5)"
    )
    assert policy.length == 24
    assert policy.max_length == 32
    assert policy.min_special == 4
    assert policy.min_upper == 5
    # Règles absentes : valeurs par défaut conservées
    assert policy.min_lower == DEFAULT_PASSWORD_POLICY.min_lower
    assert policy.min_digits == DEFAULT_PASSWORD_POLICY.min_digits


@pytest.mark.parametrize("raw", [None, "", "notUsername and passwordHistory(3)"])
def test_parse_empty_or_unsupported_policy_falls_back_to_defaults(raw) -> None:
    assert parse_password_policy(raw) == DEFAULT_PASSWORD_POLICY


# ---------------------------------------------------------------------------
# generate_password
# ---------------------------------------------------------------------------


def test_default_password_conforms_to_installer_policy() -> None:
    policy = parse_password_policy(INSTALLER_POLICY)
    for _ in range(1000):
        password = generate_password(policy)
        assert len(password) == DEFAULT_PASSWORD_LENGTH
        _assert_conforms(password, policy)


def test_password_grows_to_satisfy_strict_policy() -> None:
    policy = PasswordPolicy(
        length=30, min_upper=8, min_lower=8, min_digits=8, min_special=8
    )
    password = generate_password(policy)
    assert len(password) == 32  # somme des minimums > length
    _assert_conforms(password, policy)


def test_password_capped_by_max_length() -> None:
    policy = PasswordPolicy(length=8, max_length=12)
    for _ in range(200):
        password = generate_password(policy)
        assert len(password) == 12
        _assert_conforms(password, policy)


def test_explicit_length_below_policy_raises() -> None:
    with pytest.raises(ValueError, match="au moins 16"):
        generate_password(DEFAULT_PASSWORD_POLICY, length=12)


def test_explicit_length_above_max_raises() -> None:
    with pytest.raises(ValueError, match="au plus 12"):
        generate_password(PasswordPolicy(length=8, max_length=12), length=20)


def test_passwords_are_random() -> None:
    assert len({generate_password() for _ in range(50)}) == 50


# ---------------------------------------------------------------------------
# KeycloakService.get_password_policy
# ---------------------------------------------------------------------------


class _FakeAdminClient:
    def __init__(self, realm: dict | None = None, error: bool = False) -> None:
        self.realm = realm or {}
        self.error = error
        self.calls = 0

    def get_realm(self, realm_name: str) -> dict:
        self.calls += 1
        if self.error:
            raise KeycloakGetError("403: forbidden")
        return self.realm


def _service(admin_client: _FakeAdminClient) -> KeycloakService:
    # Pas de vrai KeycloakAdmin : on court-circuite __init__
    service = KeycloakService.__new__(KeycloakService)
    service.admin_client = admin_client
    service._password_policy = None
    return service


async def test_get_password_policy_reads_realm_and_caches() -> None:
    admin = _FakeAdminClient({"passwordPolicy": "length(24) and digits(5)"})
    service = _service(admin)

    policy = await service.get_password_policy()
    assert policy.length == 24
    assert policy.min_digits == 5

    await service.get_password_policy()
    assert admin.calls == 1

    _assert_conforms(await service.generate_password(), policy)


async def test_get_password_policy_without_view_realm_uses_defaults() -> None:
    """Sans `view-realm`, Keycloak renvoie un realm tronqué, sans passwordPolicy."""
    service = _service(_FakeAdminClient({"realm": "labomatics"}))
    assert await service.get_password_policy() == DEFAULT_PASSWORD_POLICY


async def test_get_password_policy_on_keycloak_error_uses_defaults() -> None:
    service = _service(_FakeAdminClient(error=True))
    assert await service.get_password_policy() == DEFAULT_PASSWORD_POLICY
