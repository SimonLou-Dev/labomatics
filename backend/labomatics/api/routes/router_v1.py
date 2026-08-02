"""Définitions des routes API v1."""

from fastapi import APIRouter

from labomatics.api.routes.v1.auth import router as auth_router
from labomatics.api.routes.v1.clusters import router as clusters_router
from labomatics.api.routes.v1.health import health_router_v1
from labomatics.api.routes.v1.ip_ranges import router as ip_ranges_router
from labomatics.api.routes.v1.students import router as students_router
from labomatics.api.routes.v1.vxlan_ranges import router as vxlan_ranges_router

router_v1 = APIRouter(prefix="/v1")


router_v1.include_router(health_router_v1)
router_v1.include_router(auth_router)
router_v1.include_router(students_router)
router_v1.include_router(clusters_router)
router_v1.include_router(ip_ranges_router)
router_v1.include_router(vxlan_ranges_router)
