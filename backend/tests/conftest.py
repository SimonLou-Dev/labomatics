"""Fixtures partagées pour les tests backend.

Ces tests tournent contre la vraie base Postgres/Redis locales (docker-compose),
pas contre des mocks de session SQL : il n'existe pas d'infra de test DB dédiée
dans ce projet, donc on exerce les routes/services réels.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis as RedisAsync
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from labomatics.api.deps.auth import current_user
from labomatics.api.dto.auth import AuthUser
from labomatics.api.main import app
from labomatics.core.config.settings import settings
from labomatics.core.db import session as db_session
from labomatics.services.auth_service import AuthService

# Doit être présent dans `allowed_origins` (labomatics.api.main) pour passer CSRFMiddleware.
TEST_ORIGIN = "http://localhost:5173"

_test_engine: AsyncEngine | None = None


@pytest.fixture(scope="session", autouse=True)
def _nullpool_db_engine_for_tests():
    """Crée l'engine de test (une connexion par session SQL, pas de pool).

    `pytest-asyncio` crée un event loop différent par test ; les connexions
    asyncpg sont liées à leur event loop d'origine, donc un pool de connexions
    partagé entre tests casse ("Event loop is closed") dès que pytest change
    de loop. `NullPool` ouvre/ferme une connexion neuve à chaque fois, ce qui
    évite complètement le problème (uniquement en test).
    """
    global _test_engine
    _test_engine = create_async_engine(
        settings.get_async_db_url(), echo=False, poolclass=NullPool
    )
    db_session.async_session_local.configure(bind=_test_engine)
    yield


@pytest.fixture(autouse=True)
async def _db_transaction_rollback(_nullpool_db_engine_for_tests: None):
    """Isole chaque test dans une transaction SQL annulée à la fin.

    Les repositories appellent `session.commit()` normalement (code de prod
    inchangé) ; le sessionmaker partagé est ici lié à UNE connexion + une
    transaction externe (SAVEPOINT), donc ces commits ne valident que des
    SAVEPOINTs imbriqués. À la fin du test, la transaction externe est
    annulée : rien n'est jamais réellement écrit dans la vraie base (locale
    de dev), même si un test plante en cours de route ou oublie de nettoyer
    ses propres données.
    """
    assert _test_engine is not None
    connection = await _test_engine.connect()
    transaction = await connection.begin()
    db_session.async_session_local.configure(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    yield
    await transaction.rollback()
    await connection.close()
    db_session.async_session_local.configure(bind=_test_engine)


@pytest.fixture
async def redis_client(monkeypatch: pytest.MonkeyPatch):
    """Client Redis neuf, lié à l'event loop du test courant.

    `labomatics.api.routes.v1.auth.redis_connector` est capturé une seule
    fois, au import du module, via `get_redis_async().write` — un singleton
    `@lru_cache`. Sans ce fixture, ce client reste lié à l'event loop du
    premier test qui l'a utilisé, et casse ("Event loop is closed") dès que
    pytest-asyncio passe à un autre event loop pour le test suivant.
    """
    fresh = RedisAsync(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_database,
        password=settings.redis_password,
        decode_responses=True,
    )
    monkeypatch.setattr("labomatics.api.routes.v1.auth.redis_connector", fresh)
    yield fresh
    await fresh.aclose()


@pytest.fixture
def _bypass_middleware_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralise la vérification JWT faite par `AuthMiddleware` sur chaque requête.

    Utilisée uniquement par la fixture `client` ci-dessous (tests RBAC) : la
    vérification JWT elle-même (signature, aud, issuer, azp, expiry) est
    testée indépendamment, avec le vrai `AuthService.authenticate`, dans
    `test_auth_service.py`. Le rôle effectif de chaque test HTTP est fixé via
    la fixture `override_user`.
    """
    monkeypatch.setattr(
        AuthService,
        "authenticate",
        staticmethod(
            lambda _token: AuthUser(
                subject="00000000-0000-0000-0000-000000000000",
                username="tester",
                email="tester@example.com",
                roles=[],
            )
        ),
    )


@pytest.fixture
async def client(_bypass_middleware_jwt: None) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP in-process (ASGI) contre l'app FastAPI réelle."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://localhost",
        cookies={"access_token": "fake"},
        headers={"origin": TEST_ORIGIN},
    ) as c:
        yield c
    app.dependency_overrides.pop(current_user, None)


@pytest.fixture
def override_user() -> Callable[..., AuthUser]:
    """Fixe les rôles/sujet de l'utilisateur courant pour un test donné."""

    def _set(
        roles: list[str],
        subject: str = "00000000-0000-0000-0000-000000000000",
        username: str = "tester",
    ) -> AuthUser:
        user = AuthUser(
            subject=subject,
            username=username,
            email=f"{username}@example.com",
            roles=roles,
        )
        app.dependency_overrides[current_user] = lambda: user
        return user

    return _set
