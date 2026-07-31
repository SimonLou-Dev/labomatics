from fastapi import APIRouter

health_router_v1 = APIRouter(prefix="")


@health_router_v1.get("/health")
def health() -> dict:
    """Route pour le teste de vie."""
    return {"status": "ok"}
