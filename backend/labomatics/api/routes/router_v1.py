"""Définitions des routes API v1."""

from fastapi import APIRouter

from labomatics.api.routes.v1.health import health_router_v1

router_v1 = APIRouter(prefix="/v1")


router_v1.include_router(health_router_v1)
