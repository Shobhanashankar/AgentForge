# AgentForge — Multi-Agent Task Orchestration System

A lightweight platform where four AI agents collaborate to research, write, and review complex reports.

**Pipeline:** `Planner → Researcher → Writer → Reviewer` (with review-revise loop)

---

## Quick Start

### 1. Backend (Python / FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run from project root
cd ..
uvicorn backend.main:app --reload --port 8000
```

API available at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

UI available at `http://localhost:3000`

---

## Folder Structure

```
project/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt
│   ├── agents/
│   │   ├── base.py              # BaseAgent abstract class
│   │   ├── planner.py           # PlannerAgent
│   │   ├── researcher.py        # ResearcherAgent (parallel sub-tasks)
│   │   ├── writer.py            # WriterAgent
│   │   └── reviewer.py          # ReviewerAgent
│   ├── core/
│   │   ├── models.py            # Task state machine + in-memory store
│   │   └── orchestrator.py      # Pipeline coordinator
│   └── api/
│       ├── routes.py            # REST endpoints
│       └── ws.py                # WebSocket endpoint + event emitter
│
└── frontend/
    ├── app/
    │   ├── layout.tsx           # Root layout + nav
    │   ├── page.tsx             # Homepage (task submission)
    │   ├── globals.css
    │   └── tasks/
    │       ├── page.tsx         # Task history list
    │       └── [id]/page.tsx    # Live task detail + pipeline view
    ├── components/
    │   ├── pipeline/
    │   │   ├── PipelineViz.tsx  # Animated 4-stage pipeline diagram
    │   │   ├── AgentLog.tsx     # Real-time agent event feed
    │   │   └── ReportViewer.tsx # Markdown → rendered report
    │   └── ui/
    │       └── StatusBadge.tsx  # Status pill component
    └── lib/
        ├── api.ts               # Typed fetch + WebSocket helpers
        └── types.ts             # Shared TypeScript types
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/tasks` | Submit a new task |
| `GET` | `/api/tasks` | List all tasks |
| `GET` | `/api/tasks/:id` | Get task by ID |
| `GET` | `/api/tasks/:id/report` | Get final report |
| `WS` | `/ws/tasks/:id` | Real-time event stream |

---

## Architecture Decisions

- **Async-first:** All agents are `async`, enabling the Researcher to run independent sub-tasks concurrently via `asyncio.gather`.
- **WebSocket + polling fallback:** Frontend uses WebSocket for real-time events and polls every 3s as a safety net.
- **Max 3 revision cycles:** Prevents infinite loops; best-effort report is published if cap is reached.
- **Dependency injection for emit:** The Orchestrator receives an `emit` callback, decoupling orchestration logic from FastAPI internals.

---

