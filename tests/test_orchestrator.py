"""
tests/test_orchestrator.py

Unit tests for:
  - Wave computation from dependency graph
  - Orchestrator state machine (full happy path)
  - Revision loop cap
  - skip_reviewer config
  - Agent retry logic (base agent)
  - FactCheckerAgent output structure

Run with:  pytest tests/ -v
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── 1. Wave computation ───────────────────────────────────────────────────────

from backend.core.orchestrator import _compute_waves

def test_wave_no_dependencies():
    """All tasks with no deps should collapse into a single wave."""
    subtasks = [
        {"id": "t1", "title": "A", "dependencies": []},
        {"id": "t2", "title": "B", "dependencies": []},
        {"id": "t3", "title": "C", "dependencies": []},
    ]
    waves = _compute_waves(subtasks)
    assert len(waves) == 1
    assert len(waves[0]) == 3


def test_wave_linear_chain():
    """t1 → t2 → t3 should produce 3 waves of 1 task each."""
    subtasks = [
        {"id": "t1", "title": "A", "dependencies": []},
        {"id": "t2", "title": "B", "dependencies": ["t1"]},
        {"id": "t3", "title": "C", "dependencies": ["t2"]},
    ]
    waves = _compute_waves(subtasks)
    assert len(waves) == 3
    assert waves[0][0]["id"] == "t1"
    assert waves[1][0]["id"] == "t2"
    assert waves[2][0]["id"] == "t3"


def test_wave_diamond_dependency():
    """
    t1 → t2, t3 (parallel) → t4
    Should produce: [t1], [t2, t3], [t4]
    """
    subtasks = [
        {"id": "t1", "title": "A", "dependencies": []},
        {"id": "t2", "title": "B", "dependencies": ["t1"]},
        {"id": "t3", "title": "C", "dependencies": ["t1"]},
        {"id": "t4", "title": "D", "dependencies": ["t2", "t3"]},
    ]
    waves = _compute_waves(subtasks)
    assert len(waves) == 3
    assert len(waves[1]) == 2  # t2 and t3 run in parallel
    assert waves[2][0]["id"] == "t4"


def test_wave_deadlock_guard():
    """A circular dependency should not infinite-loop (deadlock guard)."""
    subtasks = [
        {"id": "t1", "title": "A", "dependencies": ["t2"]},
        {"id": "t2", "title": "B", "dependencies": ["t1"]},
    ]
    waves = _compute_waves(subtasks)
    # Deadlock guard kicks in — at least 1 wave produced
    assert len(waves) >= 1


# ── 2. Base agent retry logic ─────────────────────────────────────────────────

from backend.agents.base import BaseAgent, AgentInput, AgentOutput, AgentStatus


class FlakyAgent(BaseAgent):
    """Fails N times then succeeds."""
    name = "FlakyAgent"

    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.attempts   = 0

    async def _execute(self, input: AgentInput) -> AgentOutput:
        self.attempts += 1
        if self.attempts <= self.fail_times:
            raise RuntimeError(f"Simulated failure #{self.attempts}")
        return AgentOutput(agent_name=self.name, status=AgentStatus.SUCCESS, message="OK")


class AlwaysFailAgent(BaseAgent):
    name = "AlwaysFailAgent"
    async def _execute(self, input: AgentInput) -> AgentOutput:
        raise RuntimeError("Always fails")


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    agent = FlakyAgent(fail_times=1)
    agent.BASE_DELAY_S = 0  # no real sleep in tests
    inp = AgentInput(task_id="x", prompt="test")
    out = await agent.run(inp)
    assert out.status == AgentStatus.SUCCESS
    assert agent.attempts == 2


@pytest.mark.asyncio
async def test_retry_exhausted_returns_failed():
    agent = AlwaysFailAgent()
    agent.MAX_RETRIES  = 3
    agent.BASE_DELAY_S = 0
    inp = AgentInput(task_id="x", prompt="test")
    out = await agent.run(inp)
    assert out.status == AgentStatus.FAILED
    assert "3 attempts" in (out.error or "")


@pytest.mark.asyncio
async def test_retry_succeeds_within_max():
    agent = FlakyAgent(fail_times=2)
    agent.MAX_RETRIES  = 3
    agent.BASE_DELAY_S = 0
    inp = AgentInput(task_id="x", prompt="test")
    out = await agent.run(inp)
    assert out.status == AgentStatus.SUCCESS


# ── 3. Orchestrator happy path ────────────────────────────────────────────────

from backend.core.models import Task, TaskStatus, PipelineConfig, task_store
from backend.core.orchestrator import Orchestrator


def _make_mock_orchestrator():
    """Return an Orchestrator with all agents mocked to succeed."""
    orc = Orchestrator()

    subtasks = [
        {"id": "t1", "title": "Background", "dependencies": [], "description": "desc", "order": 1},
        {"id": "t2", "title": "Analysis",   "dependencies": ["t1"], "description": "desc", "order": 2},
    ]

    orc.planner.run = AsyncMock(return_value=AgentOutput(
        agent_name="PlannerAgent", status=AgentStatus.SUCCESS,
        data={"subtasks": subtasks, "template_used": "default", "total_subtasks": 2},
        message="Planned",
    ))
    orc.researcher.run = AsyncMock(return_value=AgentOutput(
        agent_name="ResearcherAgent", status=AgentStatus.SUCCESS,
        data={"research_results": [{"task_id": "t1", "task_title": "Background", "findings": ["f1"], "sources": [], "confidence": 0.9},
                                   {"task_id": "t2", "task_title": "Analysis",   "findings": ["f2"], "sources": [], "confidence": 0.85}],
              "waves_executed": 2, "total_tasks_researched": 2},
        message="Researched",
    ))
    orc.writer.run = AsyncMock(return_value=AgentOutput(
        agent_name="WriterAgent", status=AgentStatus.SUCCESS,
        data={"report": "# Report\n\nContent.", "word_count": 50, "section_count": 3},
        message="Written",
    ))
    orc.reviewer.run = AsyncMock(return_value=AgentOutput(
        agent_name="ReviewerAgent", status=AgentStatus.SUCCESS,
        data={"approved": True, "score": 88, "feedback": []},
        message="Approved",
    ))
    return orc


@pytest.mark.asyncio
async def test_orchestrator_happy_path(tmp_path, monkeypatch):
    """Full pipeline runs to DONE with correct state transitions."""
    # Patch DB calls to no-ops
    monkeypatch.setattr("backend.core.models.save_task",          AsyncMock())
    monkeypatch.setattr("backend.core.models.update_task_status", AsyncMock())
    monkeypatch.setattr("backend.core.models.append_log_entry",   AsyncMock())
    monkeypatch.setattr("backend.core.models.update_task_result", AsyncMock())

    task = Task(prompt="Test query")
    orc  = _make_mock_orchestrator()
    events = []

    async def capture_emit(tid, event):
        events.append(event)

    await orc.run(task, emit=capture_emit)

    assert task.status == TaskStatus.DONE
    assert task.result is not None
    assert task.result["score"] == 88

    event_types = [e["type"] for e in events]
    assert "STATE_CHANGE"  in event_types
    assert "TASK_COMPLETE" in event_types


# ── 4. Revision loop cap ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_revision_loop_caps_at_max(monkeypatch):
    """Reviewer always rejects — loop should cap at max_revisions."""
    monkeypatch.setattr("backend.core.models.save_task",          AsyncMock())
    monkeypatch.setattr("backend.core.models.update_task_status", AsyncMock())
    monkeypatch.setattr("backend.core.models.append_log_entry",   AsyncMock())
    monkeypatch.setattr("backend.core.models.update_task_result", AsyncMock())

    cfg  = PipelineConfig(max_revisions=2)
    task = Task(prompt="Test", max_revisions=2, pipeline_config=cfg)
    orc  = _make_mock_orchestrator()

    # Reviewer always rejects
    orc.reviewer.run = AsyncMock(return_value=AgentOutput(
        agent_name="ReviewerAgent", status=AgentStatus.NEEDS_REVISION,
        data={"approved": False, "score": 40, "feedback": [{"section": "General", "comment": "Too short"}]},
        message="Rejected",
    ))

    events = []
    async def capture_emit(tid, event): events.append(event)
    await orc.run(task, emit=capture_emit)

    assert task.status == TaskStatus.DONE  # completes despite not approved
    assert task.result.get("approved") is False
    assert task.revision_count == cfg.max_revisions

    revision_events = [e for e in events if e["type"] == "REVISION_REQUESTED"]
    assert len(revision_events) == cfg.max_revisions


# ── 5. Skip reviewer config ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_skip_reviewer_bypasses_review(monkeypatch):
    """With skip_reviewer=True, ReviewerAgent.run should never be called."""
    monkeypatch.setattr("backend.core.models.save_task",          AsyncMock())
    monkeypatch.setattr("backend.core.models.update_task_status", AsyncMock())
    monkeypatch.setattr("backend.core.models.append_log_entry",   AsyncMock())
    monkeypatch.setattr("backend.core.models.update_task_result", AsyncMock())

    cfg  = PipelineConfig(skip_reviewer=True)
    task = Task(prompt="Test", pipeline_config=cfg)
    orc  = _make_mock_orchestrator()

    await orc.run(task)

    orc.reviewer.run.assert_not_called()
    assert task.status == TaskStatus.DONE
    assert task.result.get("reviewer_skipped") is True


# ── 6. FactCheckerAgent ───────────────────────────────────────────────────────

from backend.agents.fact_checker import FactCheckerAgent

@pytest.mark.asyncio
async def test_fact_checker_output_structure():
    fc  = FactCheckerAgent()
    inp = AgentInput(
        task_id="x", prompt="test",
        data={"report": "Microservices are used by 65% of companies. They always improve scalability."}
    )
    out = await fc.run(inp)
    assert out.status == AgentStatus.SUCCESS
    assert "flagged_claims"   in out.data
    assert "verified_count"   in out.data
    assert "overall_credibility" in out.data
    assert isinstance(out.data["flagged_claims"], list)