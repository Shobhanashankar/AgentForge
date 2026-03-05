"""
WebSocket endpoint — one connection per task.
Clients connect to /ws/tasks/{task_id} and receive JSON events as the
pipeline progresses.

The `emit_to_task` function is injected into the Orchestrator so it can
push events without knowing about FastAPI internals.
"""
import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])

# Map from task_id → list of active WebSocket connections
_connections: dict[str, list[WebSocket]] = defaultdict(list)
# Replay buffer so late-joining clients catch up
_event_buffer: dict[str, list[dict]] = defaultdict(list)


@router.websocket("/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    _connections[task_id].append(websocket)

    # Send buffered events so the client can reconstruct current state
    for event in _event_buffer.get(task_id, []):
        try:
            await websocket.send_text(json.dumps(event))
        except Exception:
            break

    try:
        while True:
            # Keep connection alive; client can send ping/pong
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        _connections[task_id].remove(websocket)


async def emit_to_task(task_id: str, event: dict):
    """
    Called by the Orchestrator after each state change.
    Broadcasts the event to all connected WebSocket clients and buffers it.
    """
    _event_buffer[task_id].append(event)
    dead = []
    for ws in list(_connections.get(task_id, [])):
        try:
            await ws.send_text(json.dumps(event, default=str))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections[task_id].remove(ws)
