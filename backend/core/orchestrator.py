"""
Orchestrator — manages the full agent pipeline lifecycle.
Supports user-configurable pipeline via PipelineConfig:
  - skip_reviewer:     bypass review/revision loop
  - enable_fact_check: run FactCheckerAgent after Writer
  - max_revisions:     cap the review-revise loop
"""
import asyncio
from typing import Callable, Awaitable


from ..agents import (
    AgentInput, AgentStatus,
    PlannerAgent, ResearcherAgent, WriterAgent, ReviewerAgent,
)
from ..agents.fact_checker import FactCheckerAgent
from .models import AgentLogEntry, Task, TaskStatus, PipelineConfig, task_store


EventEmitter = Callable[[str, dict], Awaitable[None]]


async def _noop_emitter(task_id: str, event: dict):
    pass


def _compute_waves(subtasks: list[dict]) -> list[list[dict]]:
    completed: set[str] = set()
    waves: list[list[dict]] = []
    remaining = list(subtasks)
    while remaining:
        wave = [t for t in remaining if all(dep in completed for dep in t.get("dependencies", []))]
        if not wave:
            wave = [remaining[0]]
        waves.append(wave)
        for t in wave:
            completed.add(t["id"])
        remaining = [t for t in remaining if t not in wave]
    return waves


class Orchestrator:
    def __init__(self):
        self.planner      = PlannerAgent()
        self.researcher   = ResearcherAgent()
        self.writer       = WriterAgent()
        self.reviewer     = ReviewerAgent()
        self.fact_checker = FactCheckerAgent()

    async def run(self, task: Task, emit: EventEmitter = _noop_emitter):
        try:
            await self._run_pipeline(task, emit)
        except Exception as exc:
            await self._fail(task, str(exc), emit)

    async def _run_pipeline(self, task: Task, emit: EventEmitter):
        cfg: PipelineConfig = task.pipeline_config

        # Emit config so frontend knows what pipeline shape to show
        await emit(task.id, {
            "type":    "PIPELINE_CONFIG",
            "agent":   "Orchestrator",
            "message": f"Pipeline configured: skip_reviewer={cfg.skip_reviewer}, fact_check={cfg.enable_fact_check}, max_revisions={cfg.max_revisions}",
            "status":  task.status,
            "payload": cfg.to_dict(),
        })

        # ── 1. PLANNING ──────────────────────────────────────────────────
        await self._transition(task, TaskStatus.PLANNING, "PlannerAgent", emit)
        planner_out = await self.planner.run(AgentInput(task_id=task.id, prompt=task.prompt))
        await self._log_agent(task, planner_out, emit)
        if planner_out.status == AgentStatus.FAILED:
            await self._fail(task, planner_out.error or "Planner failed", emit)
            return

        subtask_data = planner_out.data
        subtasks     = subtask_data.get("subtasks", [])
        waves        = _compute_waves(subtasks)

        await emit(task.id, {
            "type":    "PLAN_READY",
            "agent":   "PlannerAgent",
            "message": f"Plan ready: {len(subtasks)} sub-tasks.",
            "status":  TaskStatus.PLANNING,
            "payload": {"subtasks": subtasks, "waves": [{"wave_index": i, "tasks": w} for i, w in enumerate(waves)]},
        })

        # ── 2. RESEARCHING ───────────────────────────────────────────────
        await self._transition(task, TaskStatus.RESEARCHING, "ResearcherAgent", emit)
        await emit(task.id, {
            "type":    "WAVES_COMPUTED",
            "agent":   "ResearcherAgent",
            "message": f"{len(waves)} wave(s) of research.",
            "status":  TaskStatus.RESEARCHING,
            "payload": {"waves": [{"wave_index": i, "tasks": w} for i, w in enumerate(waves)]},
        })

        for i, wave in enumerate(waves):
            await emit(task.id, {
                "type":    "WAVE_START",
                "agent":   "ResearcherAgent",
                "message": f"Wave {i+1}/{len(waves)}: {len(wave)} task(s) in parallel.",
                "status":  TaskStatus.RESEARCHING,
                "payload": {"wave_index": i, "task_ids": [t["id"] for t in wave]},
            })

        researcher_out = await self.researcher.run(
            AgentInput(task_id=task.id, prompt=task.prompt, data=subtask_data)
        )
        await self._log_agent(task, researcher_out, emit)
        if researcher_out.status == AgentStatus.FAILED:
            await self._fail(task, researcher_out.error or "Researcher failed", emit)
            return

        research_data = researcher_out.data

        for result in research_data.get("research_results", []):
            await emit(task.id, {
                "type":    "SUBTASK_DONE",
                "agent":   "ResearcherAgent",
                "message": f"Researched: {result['task_title']}",
                "status":  TaskStatus.RESEARCHING,
                "payload": {"task_id": result["task_id"], "task_title": result["task_title"]},
            })

        # ── 3. WRITING + OPTIONAL FACT CHECK + OPTIONAL REVIEW LOOP ─────
        revision_feedback = None
        revision_count    = 0

        while True:
            # Writing
            status = TaskStatus.REVISING if revision_count > 0 else TaskStatus.WRITING
            await self._transition(task, status, "WriterAgent", emit)
            writer_out = await self.writer.run(AgentInput(
                task_id=task.id, prompt=task.prompt, data=research_data,
                revision_feedback=revision_feedback, revision_count=revision_count,
            ))
            await self._log_agent(task, writer_out, emit)
            if writer_out.status == AgentStatus.FAILED:
                await self._fail(task, writer_out.error or "Writer failed", emit)
                return

            draft_data = writer_out.data

            # ── Optional: Fact Checker ────────────────────────────────────
            if cfg.enable_fact_check:
                await self._transition(task, TaskStatus.WRITING, "FactCheckerAgent", emit)
                fc_out = await self.fact_checker.run(AgentInput(
                    task_id=task.id, prompt=task.prompt, data=draft_data,
                ))
                await self._log_agent(task, fc_out, emit)
                if fc_out.status == AgentStatus.FAILED:
                    # Fact check failure is non-fatal — log and continue
                    await emit(task.id, {
                        "type":    "FACT_CHECK_SKIPPED",
                        "agent":   "FactCheckerAgent",
                        "message": "Fact check failed, continuing with unverified draft.",
                        "status":  task.status,
                        "payload": {},
                    })
                else:
                    # Merge fact-check annotations into draft
                    draft_data = {**draft_data, "fact_check": fc_out.data}

            # ── Optional: Skip Reviewer ───────────────────────────────────
            if cfg.skip_reviewer:
                task.result = {
                    "report":          draft_data.get("report", ""),
                    "word_count":      draft_data.get("word_count", 0),
                    "score":           None,
                    "revision_count":  revision_count,
                    "subtasks":        subtasks,
                    "waves":           [{"wave_index": i, "tasks": w} for i, w in enumerate(waves)],
                    "reviewer_skipped": True,
                    "fact_check":      draft_data.get("fact_check"),
                }
                await task_store.set_result(task.id, task.result)
                await self._transition(task, TaskStatus.DONE, "Orchestrator", emit)
                await emit(task.id, {
                    "type":    "TASK_COMPLETE",
                    "agent":   "Orchestrator",
                    "message": "Task complete (reviewer skipped by user config).",
                    "status":  TaskStatus.DONE,
                    "payload": task.result,
                })
                return

            # ── Reviewing ─────────────────────────────────────────────────
            await self._transition(task, TaskStatus.REVIEWING, "ReviewerAgent", emit)
            reviewer_out = await self.reviewer.run(AgentInput(
                task_id=task.id, prompt=task.prompt, data=draft_data,
                revision_count=revision_count,
            ))
            await self._log_agent(task, reviewer_out, emit)
            if reviewer_out.status == AgentStatus.FAILED:
                await self._fail(task, reviewer_out.error or "Reviewer failed", emit)
                return

            review_data = reviewer_out.data

            if review_data.get("approved"):
                task.result = {
                    "report":          draft_data.get("report", ""),
                    "word_count":      draft_data.get("word_count", 0),
                    "score":           review_data.get("score", 0),
                    "revision_count":  revision_count,
                    "subtasks":        subtasks,
                    "waves":           [{"wave_index": i, "tasks": w} for i, w in enumerate(waves)],
                    "fact_check":      draft_data.get("fact_check"),
                }
                await task_store.set_result(task.id, task.result)
                await self._transition(task, TaskStatus.DONE, "Orchestrator", emit)
                await emit(task.id, {
                    "type":    "TASK_COMPLETE",
                    "agent":   "Orchestrator",
                    "message": f"Task completed. Score: {review_data.get('score')}/100.",
                    "status":  TaskStatus.DONE,
                    "payload": task.result,
                })
                return

            revision_count += 1
            task.revision_count = revision_count
            await emit(task.id, {
                "type":    "REVISION_REQUESTED",
                "agent":   "ReviewerAgent",
                "message": f"Revision {revision_count} requested. Score: {review_data.get('score')}/100.",
                "status":  TaskStatus.REVIEWING,
                "payload": {"feedback": review_data.get("feedback", []), "score": review_data.get("score")},
            })

            if revision_count >= cfg.max_revisions:
                task.result = {
                    "report":          draft_data.get("report", ""),
                    "word_count":      draft_data.get("word_count", 0),
                    "score":           review_data.get("score", 0),
                    "revision_count":  revision_count,
                    "approved":        False,
                    "subtasks":        subtasks,
                    "waves":           [{"wave_index": i, "tasks": w} for i, w in enumerate(waves)],
                    "note":            "Max revisions reached.",
                }
                await task_store.set_result(task.id, task.result)
                await self._transition(task, TaskStatus.DONE, "Orchestrator", emit)
                await emit(task.id, {
                    "type":    "TASK_COMPLETE",
                    "agent":   "Orchestrator",
                    "message": "Max revisions reached. Publishing best-effort report.",
                    "status":  TaskStatus.DONE,
                    "payload": task.result,
                })
                return

            revision_feedback = review_data.get("feedback", [])

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _transition(self, task: Task, status: TaskStatus, agent: str, emit: EventEmitter):
        # UPDATED: also reflect status on the Task object itself
        task.status = status
        await task_store.update_status(task.id, status)
        entry = AgentLogEntry(agent=agent, event="STATE_CHANGE", message=f"→ {status}")
        await task_store.append_log(task.id, entry)
        await emit(task.id, {"type": "STATE_CHANGE", "agent": agent, "message": entry.message, "status": status})

    async def _log_agent(self, task: Task, output, emit: EventEmitter):
        event = "AGENT_DONE" if output.status != AgentStatus.FAILED else "AGENT_FAILED"
        entry = AgentLogEntry(agent=output.agent_name, event=event, message=output.message,
                              payload=output.data if output.status == AgentStatus.SUCCESS else None)
        await task_store.append_log(task.id, entry)
        await emit(task.id, {"type": event, "agent": output.agent_name, "message": output.message,
                             "status": task.status, "duration_ms": output.duration_ms})

    async def _fail(self, task: Task, error: str, emit: EventEmitter):
        task.error = error
        await task_store.update_status(task.id, TaskStatus.FAILED)
        entry = AgentLogEntry(agent="Orchestrator", event="TASK_FAILED", message=error)
        await task_store.append_log(task.id, entry)
        await emit(task.id, {"type": "TASK_FAILED", "agent": "Orchestrator", "message": error, "status": TaskStatus.FAILED})


orchestrator = Orchestrator()
