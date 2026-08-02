"""Connecteurs Redis (sync + async), singletons, support Sentinel optionnel."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from redis import Redis, Sentinel
from redis.asyncio import Redis as RedisAsync
from redis.asyncio import Sentinel as SentinelAsync

from labomatics.core.config.settings import settings


@dataclass
class RedisClient:
    """Paire lecture/ecriture (identique hors Sentinel)."""

    read: Redis
    write: Redis


@dataclass
class RedisAsyncClient:
    read: RedisAsync
    write: RedisAsync


@lru_cache
def get_redis_sync() -> RedisClient:
    """Singleton Redis synchrone."""
    if settings.redis_sentinel_host:
        sentinel = Sentinel(
            [(settings.redis_sentinel_host, settings.redis_sentinel_port)],
            socket_timeout=0.5,
            db=settings.redis_database,
            password=settings.redis_password,
            decode_responses=True,
        )
        return RedisClient(
            read=sentinel.slave_for(settings.redis_sentinel_service),
            write=sentinel.master_for(settings.redis_sentinel_service),
        )
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_database,
        password=settings.redis_password,
        decode_responses=True,
    )
    return RedisClient(read=client, write=client)


@lru_cache
def get_redis_async() -> RedisAsyncClient:
    """Singleton Redis asynchrone."""
    if settings.redis_sentinel_host:
        sentinel = SentinelAsync(
            [(settings.redis_sentinel_host, settings.redis_sentinel_port)],
            socket_timeout=0.5,
            db=settings.redis_database,
            password=settings.redis_password,
            decode_responses=True,
        )
        return RedisAsyncClient(
            read=sentinel.slave_for(settings.redis_sentinel_service),
            write=sentinel.master_for(settings.redis_sentinel_service),
        )
    client = RedisAsync(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_database,
        password=settings.redis_password,
        decode_responses=True,
    )
    return RedisAsyncClient(read=client, write=client)
