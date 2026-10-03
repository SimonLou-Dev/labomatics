"""WebSockets pour le tracking des tâches."""

from __future__ import annotations

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from labomatics.services.task_tracking_service import TaskTrackingService
from labomatics.services.auth_service import AuthService

router = APIRouter(tags=["ws"])
task_service = TaskTrackingService()


def _get_user_from_websocket(websocket: WebSocket):
    """Extrait l'utilisateur depuis les cookies du WebSocket."""
    cookies = websocket.headers.get("cookie", "")

    for cookie in cookies.split(";"):
        cookie = cookie.strip()
        if cookie.startswith("access_token="):
            token = cookie.split("=", 1)[1]
            try:
                return AuthService.authenticate(token)
            except Exception:
                return None

    return None


@router.websocket("/ws/admin/tasks")
async def ws_admin_tasks(websocket: WebSocket) -> None:
    """WS pour les admins - liste toutes les tâches."""
    user = _get_user_from_websocket(websocket)

    if not user or ("manage_user" not in user.roles and "admin" not in user.roles):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data) if data.startswith('{') else {}

            if msg.get('type') == 'replay':
                tasks = await task_service.get_all_tasks()
                await websocket.send_json({"type": "tasks_replay", "data": tasks})
            elif data == "ping" or msg.get('type') == 'ping':
                tasks = await task_service.get_all_tasks()
                await websocket.send_json({"type": "tasks_update", "data": tasks})
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/user/tasks")
async def ws_user_tasks(websocket: WebSocket) -> None:
    """WS pour les users - toutes les tâches si admin, sinon ses propres tâches."""
    await websocket.accept()

    user = _get_user_from_websocket(websocket)

    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    import logging
    logger = logging.getLogger(__name__)

    # Vérifier si l'utilisateur est admin
    is_admin = "manage_user" in user.roles or "admin" in user.roles
    user_id_filter = None if is_admin else str(user.subject)

    logger.info(f"WS user/tasks connected: user_id={user.subject}, is_admin={is_admin}")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data) if data.startswith('{') else {}

            if msg.get('type') == 'replay':
                logger.info(f"Replay requested for user {user.subject} (admin={is_admin})")
                tasks = await task_service.get_all_tasks(user_id=user_id_filter)
                logger.info(f"Found {len(tasks.get('in_progress', []))} in_progress, {len(tasks.get('errors', []))} errors")
                await websocket.send_json({"type": "tasks_replay", "data": tasks})
            elif data == "ping" or msg.get('type') == 'ping':
                tasks = await task_service.get_all_tasks(user_id=user_id_filter)
                await websocket.send_json({"type": "tasks_update", "data": tasks})
    except WebSocketDisconnect:
        pass
