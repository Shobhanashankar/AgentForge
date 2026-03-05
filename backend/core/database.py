"""
database.py — Async SQLite persistence for task state.
Uses aiosqlite so it never blocks the FastAPI event loop.

Install: pip install aiosqlite
"""
import json
import asyncio
from datetime import datetime
from typing import Optional
import aiosqlite

DB_PATH = "agent_forge.db"

# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    prompt          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'IDLE',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    revision_count  INTEGER NOT NULL DEFAULT 0,
    max_revisions   INTEGER NOT NULL DEFAULT 3,
    result          TEXT,          -- JSON blob
    error           TEXT,
    agent_log       TEXT NOT NULL DEFAULT '[]',  -- JSON array
    pipeline_config TEXT NOT NULL DEFAULT '{}'   -- JSON blob
);
"""

# ── Public API ────────────────────────────────────────────────────────────────

async def init_db():
    """Create tables on startup. Safe to call multiple times."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()
    print(f"[DB] Initialized at {DB_PATH}")


async def save_task(task_dict: dict):
    """Insert or replace a full task object."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO tasks
              (id, prompt, status, created_at, updated_at, revision_count,
               max_revisions, result, error, agent_log, pipeline_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_dict["id"],
                task_dict["prompt"],
                task_dict["status"],
                task_dict.get("created_at", datetime.utcnow().isoformat()),
                datetime.utcnow().isoformat(),
                task_dict.get("revision_count", 0),
                task_dict.get("max_revisions", 3),
                json.dumps(task_dict.get("result")) if task_dict.get("result") else None,
                task_dict.get("error"),
                json.dumps(task_dict.get("agent_log", [])),
                json.dumps(task_dict.get("pipeline_config", {})),
            ),
        )
        await db.commit()


async def update_task_status(task_id: str, status: str):
    """Fast partial update — only touches status + updated_at."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.utcnow().isoformat(), task_id),
        )
        await db.commit()


async def update_task_result(task_id: str, result: dict):
    """Store final result JSON."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tasks SET result = ?, updated_at = ? WHERE id = ?",
            (json.dumps(result), datetime.utcnow().isoformat(), task_id),
        )
        await db.commit()


async def append_log_entry(task_id: str, entry: dict):
    """Append one log entry to the agent_log JSON array."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT agent_log FROM tasks WHERE id = ?", (task_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            log = json.loads(row[0] or "[]")
            log.append(entry)
            await db.execute(
                "UPDATE tasks SET agent_log = ?, updated_at = ? WHERE id = ?",
                (json.dumps(log), datetime.utcnow().isoformat(), task_id),
            )
            await db.commit()


async def get_task(task_id: str) -> Optional[dict]:
    """Fetch a single task by ID. Returns None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def list_tasks(limit: int = 50) -> list[dict]:
    """Return the most recent `limit` tasks, newest first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    d = dict(row)
    d["result"]          = json.loads(d["result"])    if d.get("result")          else None
    d["agent_log"]       = json.loads(d["agent_log"]) if d.get("agent_log")       else []
    d["pipeline_config"] = json.loads(d["pipeline_config"]) if d.get("pipeline_config") else {}
    return d