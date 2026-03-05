"""
REST endpoints:
  POST   /tasks          — submit a new task
  GET    /tasks          — list all tasks
  GET    /tasks/{id}     — get task by ID
  GET    /tasks/{id}/report — get final report
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from ..core.models import task_store
from ..core.orchestrator import orchestrator
from .ws import emit_to_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


class SubmitRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=2000)


@router.post("", status_code=202)
async def submit_task(body: SubmitRequest, background_tasks: BackgroundTasks):
    task = await task_store.create(prompt=body.prompt)
    background_tasks.add_task(orchestrator.run, task, emit_to_task)
    return {"task_id": task.id, "status": task.status, "prompt": task.prompt}


@router.get("")
async def list_tasks():
    tasks = await task_store.list_all()
    return [
        {
            "id": t.id,
            "prompt": t.prompt,
            "status": t.status,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "revision_count": t.revision_count,
        }
        for t in sorted(tasks, key=lambda x: x.created_at, reverse=True)
    ]


@router.get("/{task_id}")
async def get_task(task_id: str):
    task = await task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@router.get("/{task_id}/report")
async def get_report(task_id: str):
    task = await task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.result:
        raise HTTPException(status_code=404, detail="Report not yet available")
    return task.result
