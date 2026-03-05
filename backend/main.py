"""
main.py — FastAPI application entry point.
Adds: DB init on startup, pipeline_config in POST /tasks, task history endpoint.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from .core.database import init_db
from .core.models import PipelineConfig, TaskStatus, task_store
from .core.orchestrator import orchestrator


# ── Lifespan: init DB + restore task history on startup ──────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await task_store.load_from_db()
    yield


app = FastAPI(title="Agent Forge API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection registry
_connections: dict[str, list[WebSocket]] = {}


# ── Request / Response schemas ────────────────────────────────────────────────

class PipelineConfigSchema(BaseModel):
    skip_reviewer:     bool = False
    max_revisions:     int  = Field(default=3, ge=1, le=5)
    enable_fact_check: bool = False


class SubmitTaskRequest(BaseModel):
    prompt:          str
    pipeline_config: Optional[PipelineConfigSchema] = None


class TaskSummary(BaseModel):
    task_id: str
    status:  str
    prompt:  str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/tasks", response_model=TaskSummary)
async def submit_task(body: SubmitTaskRequest):
    if len(body.prompt.strip()) < 10:
        raise HTTPException(400, "Prompt must be at least 10 characters.")

    cfg = PipelineConfig()
    if body.pipeline_config:
        cfg = PipelineConfig(
            skip_reviewer=body.pipeline_config.skip_reviewer,
            max_revisions=body.pipeline_config.max_revisions,
            enable_fact_check=body.pipeline_config.enable_fact_check,
        )

    task = await task_store.create(prompt=body.prompt.strip(), config=cfg)

    async def emit(task_id: str, event: dict):
        for ws in _connections.get(task_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                pass

    asyncio.create_task(orchestrator.run(task, emit=emit))

    return TaskSummary(task_id=task.id, status=task.status, prompt=task.prompt)


@app.get("/api/tasks")
async def list_tasks():
    tasks = await task_store.list_all()
    return [t.to_dict() for t in tasks]


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = await task_store.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found.")
    return task.to_dict()


@app.websocket("/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    _connections.setdefault(task_id, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections[task_id].remove(websocket)