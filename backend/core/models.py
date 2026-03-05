"""
models.py — Task data model + in-memory store with SQLite persistence.
The in-memory dict is the primary read path (fast).
SQLite is the write-through persistence layer (durable).
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .database import (
    save_task, update_task_status, update_task_result,
    append_log_entry, get_task as db_get_task, list_tasks as db_list_tasks,
)


class TaskStatus(str, Enum):
    IDLE       = "IDLE"
    PLANNING   = "PLANNING"
    RESEARCHING = "RESEARCHING"
    WRITING    = "WRITING"
    REVIEWING  = "REVIEWING"
    REVISING   = "REVISING"
    DONE       = "DONE"
    FAILED     = "FAILED"


@dataclass
class AgentLogEntry:
    agent:   str
    event:   str
    message: str
    payload: Any   = None
    ts:      str   = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "agent":   self.agent,
            "event":   self.event,
            "message": self.message,
            "payload": self.payload,
            "ts":      self.ts,
        }


@dataclass
class PipelineConfig:
    """User-configurable pipeline options."""
    skip_reviewer:    bool = False
    max_revisions:    int  = 3
    enable_fact_check: bool = False   # stretch: adds FactCheckerAgent after Writer

    def to_dict(self) -> dict:
        return {
            "skip_reviewer":    self.skip_reviewer,
            "max_revisions":    self.max_revisions,
            "enable_fact_check": self.enable_fact_check,
        }

    @staticmethod
    def from_dict(d: dict) -> "PipelineConfig":
        return PipelineConfig(
            skip_reviewer=d.get("skip_reviewer", False),
            max_revisions=d.get("max_revisions", 3),
            enable_fact_check=d.get("enable_fact_check", False),
        )


@dataclass
class Task:
    prompt:          str
    id:              str            = field(default_factory=lambda: str(uuid.uuid4()))
    status:          TaskStatus     = TaskStatus.IDLE
    created_at:      str            = field(default_factory=lambda: datetime.utcnow().isoformat())
    revision_count:  int            = 0
    max_revisions:   int            = 3
    agent_log:       list           = field(default_factory=list)
    result:          Optional[dict] = None
    error:           Optional[str]  = None
    pipeline_config: PipelineConfig = field(default_factory=PipelineConfig)

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "prompt":          self.prompt,
            "status":          self.status,
            "created_at":      self.created_at,
            "revision_count":  self.revision_count,
            "max_revisions":   self.max_revisions,
            "agent_log":       [e.to_dict() if hasattr(e, "to_dict") else e for e in self.agent_log],
            "result":          self.result,
            "error":           self.error,
            "pipeline_config": self.pipeline_config.to_dict(),
        }


class TaskStore:
    """
    In-memory task store with write-through SQLite persistence.
    On startup, call load_from_db() to restore previous session tasks.
    """

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()

    # ── Write ops ─────────────────────────────────────────────────────────────

    async def create(self, prompt: str, config: PipelineConfig | None = None) -> Task:
        cfg = config or PipelineConfig()
        task = Task(
            prompt=prompt,
            max_revisions=cfg.max_revisions,
            pipeline_config=cfg,
        )
        async with self._lock:
            self._tasks[task.id] = task
        # Persist immediately
        await save_task(task.to_dict())
        return task

    async def update_status(self, task_id: str, status: TaskStatus):
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].status = status
        await update_task_status(task_id, status)

    async def append_log(self, task_id: str, entry: AgentLogEntry):
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].agent_log.append(entry)
        await append_log_entry(task_id, entry.to_dict())

    async def set_result(self, task_id: str, result: dict):
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].result = result
        await update_task_result(task_id, result)

    # ── Read ops ──────────────────────────────────────────────────────────────

    async def get(self, task_id: str) -> Optional[Task]:
        async with self._lock:
            task = self._tasks.get(task_id)
        if task:
            return task
        # Fallback: check SQLite (task was created in a previous session)
        row = await db_get_task(task_id)
        return _dict_to_task(row) if row else None

    async def list_all(self) -> list[Task]:
        # Merge in-memory + DB (DB is authoritative for old tasks)
        rows = await db_list_tasks(limit=100)
        tasks = []
        async with self._lock:
            mem_ids = set(self._tasks.keys())
        for row in rows:
            if row["id"] in mem_ids:
                async with self._lock:
                    tasks.append(self._tasks[row["id"]])
            else:
                tasks.append(_dict_to_task(row))
        return tasks

    async def load_from_db(self):
        """
        Call once on startup to restore completed/failed tasks from SQLite
        into memory so GET /tasks returns history across restarts.
        """
        rows = await db_list_tasks(limit=200)
        async with self._lock:
            for row in rows:
                if row["id"] not in self._tasks:
                    self._tasks[row["id"]] = _dict_to_task(row)
        print(f"[TaskStore] Loaded {len(rows)} task(s) from SQLite.")


def _dict_to_task(d: dict) -> Task:
    cfg = PipelineConfig.from_dict(d.get("pipeline_config") or {})
    t = Task(
        prompt=d["prompt"],
        id=d["id"],
        status=TaskStatus(d["status"]),
        created_at=d["created_at"],
        revision_count=d.get("revision_count", 0),
        max_revisions=d.get("max_revisions", 3),
        agent_log=d.get("agent_log", []),
        result=d.get("result"),
        error=d.get("error"),
        pipeline_config=cfg,
    )
    return t


# Singleton
task_store = TaskStore()