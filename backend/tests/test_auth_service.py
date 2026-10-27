"""Tests unitaires — issue #75 : vérification TLS/JWT.

Keycloak est entièrement mocké (JWKS + endpoints token), donc ces tests ne
dépendent ni du réseau ni du certificat auto-signé réel de Keycloak.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import jwt
import pytest
import requests
import responses
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from labomatics.api.dto.auth import AuthUser
from labomatics.core.config.settings import settings
from labomatics.services.auth_service import AuthService

KID = "test-kid-1"
CLIENT_ID = settings.keycloak_client_id
ISSUER = f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"
CERTS_URL = f"{ISSUER}/protocol/openid-connect/certs"


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.fixture(scope="module")
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture(scope="module")
def jwk(rsa_keypair):
    _private_key, public_key = rsa_keypair
    numbers = public_key.public_numbers()
    return {
        "kty": "RSA",
        "kid": KID,
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_uint(numbers.n),
        "e": _b64url_uint(numbers.e),
    }


@pytest.fixture(autouse=True)
def _reset_jwks_cache():
    """`_jwks_cache`/`_jwks_fetched_at` sont des attributs de classe partagés."""
    AuthService._jwks_cache = None
    AuthService._jwks_fetched_at = 0.0
    yield
    AuthService._jwks_cache = None
    AuthService._jwks_fetched_at = 0.0


def _make_token(rsa_keypair, *, roles: list[str] | None = None, **overrides) -> str:
    private_key, _public_key = rsa_keypair
    now = datetime.now(UTC)
    payload = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "preferred_username": "etudiant1",
        "email": "etudiant1@test.local",
        "realm_access": {"roles": roles or ["student"]},
        "aud": CLIENT_ID,
        "azp": CLIENT_ID,
        "iss": ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(overrides)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": KID})


# ---------------------------------------------------------------------------
# Vérification JWT (signature, audience, issuer, azp, expiry)
# ---------------------------------------------------------------------------


@responses.activate
def test_authenticate_valid_token_returns_user(rsa_keypair, jwk):
    responses.get(CERTS_URL, json={"keys": [jwk]})
    token = _make_token(rsa_keypair, roles=["student", "manage_user"])

    user = AuthService.authenticate(token)

    assert user.subject == "11111111-1111-1111-1111-111111111111"
    assert user.username == "etudiant1"
    assert "manage_user" in user.roles


@responses.activate
def test_authenticate_rejects_wrong_azp(rsa_keypair, jwk):
    responses.get(CERTS_URL, json={"keys": [jwk]})
    token = _make_token(rsa_keypair, azp="un-autre-client")

    with pytest.raises(HTTPException) as exc_info:
        AuthService.authenticate(token)
    assert exc_info.value.status_code == 401


@responses.activate
def test_authenticate_rejects_wrong_audience(rsa_keypair, jwk):
    responses.get(CERTS_URL, json={"keys": [jwk]})
    token = _make_token(rsa_keypair, aud="un-autre-client")

    with pytest.raises(HTTPException) as exc_info:
        AuthService.authenticate(token)
    assert exc_info.value.status_code == 401


@responses.activate
def test_authenticate_rejects_wrong_issuer(rsa_keypair, jwk):
    responses.get(CERTS_URL, json={"keys": [jwk]})
    token = _make_token(
        rsa_keypair, iss="https://keycloak-pirate.invalid/realms/labomatics"
    )

    with pytest.raises(HTTPException) as exc_info:
        AuthService.authenticate(token)
    assert exc_info.value.status_code == 401


@responses.activate
def test_authenticate_rejects_expired_token(rsa_keypair, jwk):
    responses.get(CERTS_URL, json={"keys": [jwk]})
    now = datetime.now(UTC)
    token = _make_token(
        rsa_keypair, iat=now - timedelta(hours=2), exp=now - timedelta(hours=1)
    )

    with pytest.raises(HTTPException) as exc_info:
        AuthService.authenticate(token)
    assert exc_info.value.status_code == 401


@responses.activate
def test_authenticate_rejects_token_signed_by_unknown_key(jwk):
    """Un token signé par une clé jamais publiée dans la JWKS est refusé."""
    responses.get(CERTS_URL, json={"keys": [jwk]})
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    payload = {
        "sub": "x",
        "aud": CLIENT_ID,
        "azp": CLIENT_ID,
        "iss": ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    # Signé avec `other_key`, mais annonce le `kid` de la clé publiée (usurpation).
    token = jwt.encode(payload, other_key, algorithm="RS256", headers={"kid": KID})

    with pytest.raises(HTTPException) as exc_info:
        AuthService.authenticate(token)
    assert exc_info.value.status_code == 401


def test_authenticate_rejects_missing_token():
    with pytest.raises(HTTPException) as exc_info:
        AuthService.authenticate(None)
    assert exc_info.value.status_code == 401


@responses.activate
def test_jwks_is_cached_across_calls(rsa_keypair, jwk):
    """Deux authentifications rapprochées n'interrogent Keycloak qu'une fois."""
    rsp = responses.get(CERTS_URL, json={"keys": [jwk]})
    token = _make_token(rsa_keypair)

    AuthService.authenticate(token)
    AuthService.authenticate(token)

    assert rsp.call_count == 1


@responses.activate
def test_unknown_kid_forces_jwks_refresh_before_failing(rsa_keypair, jwk):
    """Un `kid` absent du cache déclenche un rechargement avant d'échouer."""
    rsp = responses.get(CERTS_URL, json={"keys": [jwk]})
    private_key, _ = rsa_keypair
    now = datetime.now(UTC)
    payload = {
        "sub": "x",
        "aud": CLIENT_ID,
        "azp": CLIENT_ID,
        "iss": ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    token = jwt.encode(
        payload, private_key, algorithm="RS256", headers={"kid": "kid-inconnu"}
    )

    with pytest.raises(HTTPException) as exc_info:
        AuthService.authenticate(token)

    assert exc_info.value.status_code == 401
    # 1er appel (cache vide) + 1 rechargement forcé puisque ce kid n'y figure pas.
    assert rsp.call_count == 2


# ---------------------------------------------------------------------------
# Vérification TLS : plus aucun `verify=False` en dur
# ---------------------------------------------------------------------------


def test_tls_verify_is_propagated_to_jwks_request(monkeypatch):
    captured = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"keys": []}

    def _fake_get(_url, verify=None, timeout=None):
        captured["verify"] = verify
        return _FakeResponse()

    monkeypatch.setattr(requests, "get", _fake_get)
    AuthService._get_public_keys(force_refresh=True)

    assert captured["verify"] == settings.tls_verify
    assert captured["verify"] is not False


# ---------------------------------------------------------------------------
# Échange de code (PKCE) / refresh / révocation (renouvellement de session)
# ---------------------------------------------------------------------------


class _FakeTokenResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


def test_exchange_code_for_token_sends_pkce_verifier(monkeypatch):
    captured = {}

    def _fake_post(url, data=None, verify=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        captured["verify"] = verify
        return _FakeTokenResponse({"access_token": "abc", "refresh_token": "def"})

    monkeypatch.setattr(requests, "post", _fake_post)

    result = AuthService.exchange_code_for_token(
        "the-code", code_verifier="the-verifier"
    )

    assert result["access_token"] == "abc"
    assert captured["data"]["code"] == "the-code"
    assert captured["data"]["code_verifier"] == "the-verifier"
    assert captured["verify"] == settings.tls_verify


def test_refresh_access_token_sends_refresh_grant(monkeypatch):
    """Renouvellement de session : le refresh token doit produire un nouveau
    couple access/refresh, avec sa propre durée de vie (`refresh_expires_in`)."""
    captured = {}

    def _fake_post(url, data=None, verify=None, timeout=None):
        captured["data"] = data
        return _FakeTokenResponse(
            {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 60,
                "refresh_expires_in": 1800,
            }
        )

    monkeypatch.setattr(requests, "post", _fake_post)

    result = AuthService.refresh_access_token("old-refresh-token")

    assert captured["data"]["grant_type"] == "refresh_token"
    assert captured["data"]["refresh_token"] == "old-refresh-token"
    assert result["access_token"] == "new-access"
    assert result["refresh_expires_in"] == 1800


def test_revoke_refresh_token_calls_keycloak_logout_endpoint(monkeypatch):
    captured = {}

    def _fake_post(url, data=None, verify=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return _FakeTokenResponse({})

    monkeypatch.setattr(requests, "post", _fake_post)

    AuthService.revoke_refresh_token("a-refresh-token")

    assert captured["url"].endswith("/protocol/openid-connect/logout")
    assert captured["data"]["refresh_token"] == "a-refresh-token"
    assert captured["data"]["client_id"] == settings.keycloak_client_id


def _user_with_roles(roles: list[str]) -> AuthUser:
    return AuthUser(
        subject="00000000-0000-0000-0000-000000000000",
        username="tester",
        email="tester@example.com",
        roles=roles,
    )


def test_ensure_any_role_passes_with_one_matching_role():
    user = _user_with_roles(["admin"])
    assert AuthService.ensure_any_role(user, "teacher", "admin") is user


def test_ensure_any_role_rejects_when_no_role_matches():
    user = _user_with_roles(["student"])
    with pytest.raises(HTTPException) as exc_info:
        AuthService.ensure_any_role(user, "teacher", "admin")
    assert exc_info.value.status_code == 403
