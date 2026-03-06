# AgentForge — Multi-Agent Task Orchestration System

A lightweight platform where five AI agents collaborate to research, write, and review complex reports — with a user-configurable pipeline, real-time WebSocket updates, parallel sub-task wave execution, SQLite persistence, and a polished Next.js frontend.

**Pipeline:** `Planner → Researcher → Writer → [Fact Checker*] → Reviewer` (with review-revise loop)
---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (**64-bit** — required for Next.js SWC compiler on Windows)

### 1. Backend (Python / FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install aiosqlite              # SQLite persistence layer

# Run from project root
cd ..
uvicorn backend.main:app --reload --port 8000
```

API available at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

> On first run, `agent_forge.db` is created automatically in the project root.  
> On restart, all previous tasks and reports are restored from SQLite automatically.

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

UI available at `http://localhost:3000`

### 3. Run Tests

```bash
# From project root
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## Folder Structure

```
project/
├── backend/
│   ├── main.py                        # FastAPI app + DB init lifespan + pipeline_config in POST /tasks
│   ├── requirements.txt
│   ├── agent_forge.db                 # Auto-created SQLite database 
│   │
│   ├── agents/
│   │   ├── base.py                    # BaseAgent + exponential backoff retry (3 attempts, 1s→2s→4s)
│   │   ├── planner.py                 # PlannerAgent — topic-aware subtask decomposition
│   │   ├── researcher.py              # ResearcherAgent — dependency wave + asyncio.gather
│   │   ├── writer.py                  # WriterAgent — dynamic report with revision changelog
│   │   ├── reviewer.py                # ReviewerAgent — content-aware scoring & feedback
│   │   └── fact_checker.py            # FactCheckerAgent — claim verification 
│   │
│   ├── core/
│   │   ├── database.py                # Async SQLite layer (aiosqlite) — CRUD helpers
│   │   ├── models.py                 
│   │   └── orchestrator.py           
│   │
│   └── api/
│       ├── routes.py                  # REST endpoints
│       └── ws.py                      # WebSocket endpoint + event emitter
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                
│   │   ├── page.tsx                   
│   │   ├── globals.css                
│   │   └── tasks/
│   │       ├── page.tsx               
│   │       └── [id]/page.tsx          
│   │
│   ├── components/
│   │   ├── pipeline/
│   │   │   ├── PipelineViz.tsx        
│   │   │   ├── PipelineConfigPanel.tsx 
│   │   │   ├── AgentLog.tsx           
│   │   │   └── ReportViewer.tsx       
│   │   └── ui/
│   │       └── StatusBadge.tsx        
│   │
│   └── lib/
│       ├── api.ts                    
│       └── types.ts                  
│
└── tests/
    ├── test_orchestrator.py           
    └── pytest.ini                     
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tasks` | Submit a new task with `pipeline_config` |
| `GET` | `/api/tasks` | List all tasks (persisted across restarts) |
| `GET` | `/api/tasks/:id` | Get task by ID |
| `WS` | `/ws/tasks/:id` | Real-time WebSocket event stream |

### POST /api/tasks — Request Body

```json
{
  "prompt": "Compare REST vs GraphQL API design approaches",
  "pipeline_config": {
    "skip_reviewer":     false,
    "max_revisions":     3,
    "enable_fact_check": false
  }
}
```

### WebSocket Events

| Event | Description |
|---|---|
| `STATE_CHANGE` | Pipeline state transition |
| `PIPELINE_CONFIG` | Active config emitted at pipeline start |
| `PLAN_READY` | Subtask list + wave graph from Planner |
| `WAVES_COMPUTED` | Dependency wave graph sent to frontend |
| `WAVE_START` | Wave executing — task IDs in payload |
| `SUBTASK_DONE` | Individual subtask completed with confidence |
| `REVISION_REQUESTED` | Reviewer rejected — feedback items attached |
| `FACT_CHECK_SKIPPED` | Fact check failed non-fatally |
| `TASK_COMPLETE` | Final report ready — full result payload |
| `TASK_FAILED` | Unrecoverable error after retry exhaustion |

---

## Pipeline Configuration

Configurable from the home page before submitting — no code changes needed:

| Option | Default | Description |
|---|---|---|
| **Skip Reviewer** | Off | Publish draft immediately without scoring or revision cycles |
| **Enable Fact Checker** | Off | Add FactCheckerAgent after Writer to verify quantitative claims |
| **Max Revisions** | 3 | Cap on review-revise cycles (slider: 1–5) |

---

## Agent Overview

| Agent | Role | Key Behaviour |
|---|---|---|
| **PlannerAgent** | Decomposes prompt into subtasks | Detects comparison / research / default templates; extracts topic and injects it into all subtask titles and descriptions |
| **ResearcherAgent** | Researches each subtask | Groups subtasks into dependency waves; runs each wave concurrently with `asyncio.gather()` |
| **WriterAgent** | Synthesises research into a report | Produces topic-specific executive summary and conclusion; appends revision changelog on rewrites |
| **ReviewerAgent** | Scores and critiques the draft | Scans actual report content for shallow summaries, missing metrics, and comparison gaps; generates targeted feedback |
| **FactCheckerAgent** | Verifies quantitative claims |  Non-fatal — pipeline emits `FACT_CHECK_SKIPPED` and continues if it errors |

All agents inherit from `BaseAgent`, which provides **exponential backoff retry** (3 attempts, delays: 1 s → 2 s → 4 s). Permanent failure returns a graceful `FAILED` output rather than raising.

---

## Architecture Decisions

**Async-first throughout**  
All agents are `async`. The Researcher runs independent subtasks concurrently via `asyncio.gather()`. An `asyncio.Lock()` on `TaskStore` prevents race conditions during concurrent WebSocket reads/writes.

**Wave-based parallel execution**  
The Orchestrator pre-computes execution waves from the subtask dependency graph before research begins. Each wave is emitted as a `WAVE_START` event so the UI visualises which tasks run in parallel vs. sequentially.

**WebSocket + polling fallback**  
WebSocket is the primary real-time channel — events push instantly as each agent completes. A 3-second polling interval runs in parallel as a safety net for unstable connections.

**Write-through SQLite persistence**  
Every state change is immediately written to `agent_forge.db`. On restart, `task_store.load_from_db()` restores all tasks into memory — the `/tasks` history page works across restarts with no user action.

**PipelineConfig as a first-class model**  
User pipeline preferences are stored on each `Task`, persisted to SQLite, and emitted at pipeline start. The Orchestrator reads config at each decision point — adding a new toggle requires changing one agent and one config field, not the Orchestrator core.

**Dependency injection for emit**  
The Orchestrator receives an `emit` callback injected by the API layer. This decouples orchestration logic from FastAPI's WebSocket internals and makes the Orchestrator independently unit-testable.

---

## Testing

```bash
pytest tests/ -v
```

11 tests covering:

| Test | What it verifies |
|---|---|
| `test_wave_no_dependencies` | All independent tasks collapse to 1 wave |
| `test_wave_linear_chain` | A → B → C produces 3 sequential waves |
| `test_wave_diamond_dependency` | Diamond graph produces correct parallel wave |
| `test_wave_deadlock_guard` | Circular deps don't cause infinite loop |
| `test_retry_succeeds_on_second_attempt` | Flaky agent recovers on retry 2 |
| `test_retry_exhausted_returns_failed` | Permanent failure returns FAILED gracefully |
| `test_retry_succeeds_within_max` | 2 failures + 1 success within 3-attempt cap |
| `test_orchestrator_happy_path` | Full pipeline → DONE with correct score |
| `test_revision_loop_caps_at_max` | Loop stops at max_revisions, publishes best-effort |
| `test_skip_reviewer_bypasses_review` | ReviewerAgent never called, task still DONE |
| `test_fact_checker_output_structure` | FactCheckerAgent returns correct payload shape |

---

## Stretch Goals Implemented

| Goal | Status | Details |
|---|---|---|
| Retry / error handling | ✅ Done | Exponential backoff in `BaseAgent`; graceful FAILED state on exhaustion |
| Parallel agents | ✅ Done | Wave-based concurrent research with live frontend wave visualization |
| Agent configuration | ✅ Done | Toggle panel: skip reviewer, add fact checker, set revision cap (1–5) |
| Persistent state | ✅ Done | SQLite via `aiosqlite`; task history survives server restarts |
| Unit tests | ✅ Done | 11 pytest tests — orchestrator, retry, wave graph, config branching |
