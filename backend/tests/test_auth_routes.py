"""Tests d'intégration — issue #75 : routes /login, /callback, /logout.

Keycloak (échange de code / révocation) est mocké via `AuthService` ; Redis
(state OAuth2 + PKCE verifier) est le vrai Redis local (docker-compose).
"""

from __future__ import annotations

from urllib.parse import parse_qs, quote, urlparse

from labomatics.core.config.settings import settings
from labomatics.services.auth_service import AuthService


def _state_from_location(location: str) -> str:
    query = parse_qs(urlparse(location).query)
    return query["state"][0]


async def test_login_redirects_with_pkce_and_stores_state(client, redis_client):
    resp = await client.get(
        "/v1/auth/login?redirect=/dashboard", follow_redirects=False
    )

    assert resp.status_code == 307 or resp.status_code == 302
    location = resp.headers["location"]
    query = parse_qs(urlparse(location).query)

    assert query["code_challenge_method"][0] == "S256"
    assert "code_challenge" in query
    state = query["state"][0]

    assert await redis_client.get(f"oauth2:state:{state}") == "/dashboard"
    verifier = await redis_client.get(f"oauth2:verifier:{state}")
    assert verifier and len(verifier) > 20


async def test_login_neutralizes_cross_origin_redirect(client, redis_client):
    resp = await client.get(
        "/v1/auth/login?redirect=https://evil.example.com/steal",
        follow_redirects=False,
    )
    state = _state_from_location(resp.headers["location"])

    assert await redis_client.get(f"oauth2:state:{state}") == "/"


async def test_login_allows_same_origin_absolute_redirect(client, redis_client):
    same_origin_redirect = f"{settings.front_url}/#/dashboard"
    resp = await client.get(
        f"/v1/auth/login?redirect={quote(same_origin_redirect, safe='')}",
        follow_redirects=False,
    )
    state = _state_from_location(resp.headers["location"])

    assert await redis_client.get(f"oauth2:state:{state}") == same_origin_redirect


async def test_callback_exchanges_code_sets_cookies_and_redirects(
    client, redis_client, monkeypatch
):
    state = "test-state-callback-1"
    await redis_client.set(f"oauth2:state:{state}", "/dashboard", ex=600)
    await redis_client.set(f"oauth2:verifier:{state}", "the-verifier", ex=600)

    captured = {}

    def _fake_exchange(code, code_verifier=None):
        captured["code"] = code
        captured["code_verifier"] = code_verifier
        return {
            "access_token": "AT123",
            "refresh_token": "RT456",
            "expires_in": 60,
            "refresh_expires_in": 1800,
        }

    monkeypatch.setattr(AuthService, "exchange_code_for_token", _fake_exchange)

    resp = await client.get(
        f"/v1/auth/callback?code=the-code&state={state}", follow_redirects=False
    )

    assert resp.status_code == 302
    assert resp.headers["location"] == "/dashboard"
    assert captured["code"] == "the-code"
    assert captured["code_verifier"] == "the-verifier"

    set_cookie_headers = "\n".join(resp.headers.get_list("set-cookie"))
    assert "access_token=AT123" in set_cookie_headers
    assert "refresh_token=RT456" in set_cookie_headers
    assert "Max-Age=60" in set_cookie_headers
    assert "Max-Age=1800" in set_cookie_headers

    # State et verifier consommés (anti-replay).
    assert await redis_client.get(f"oauth2:state:{state}") is None
    assert await redis_client.get(f"oauth2:verifier:{state}") is None


async def test_callback_rejects_invalid_state(client, redis_client):
    resp = await client.get(
        "/v1/auth/callback?code=whatever&state=unknown-state", follow_redirects=False
    )
    assert resp.status_code == 400


async def test_logout_revokes_refresh_token_and_deletes_cookies(client, monkeypatch):
    captured = {}

    def _fake_revoke(refresh_token):
        captured["refresh_token"] = refresh_token

    monkeypatch.setattr(AuthService, "revoke_refresh_token", _fake_revoke)

    client.cookies.set("refresh_token", "RT-to-revoke")
    resp = await client.get("/v1/auth/logout", follow_redirects=False)

    assert resp.status_code == 302
    assert captured["refresh_token"] == "RT-to-revoke"

    location = resp.headers["location"]
    assert location.startswith(
        f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/logout"
    )
    assert f"redirect_uri={settings.front_url}" in location

    set_cookie_headers = "\n".join(resp.headers.get_list("set-cookie"))
    assert "access_token=" in set_cookie_headers
    assert "refresh_token=" in set_cookie_headers
    # `delete_cookie` pose un cookie déjà expiré (Max-Age=0).
    assert "Max-Age=0" in set_cookie_headers
