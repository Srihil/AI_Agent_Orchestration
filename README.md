# Agent Orchestration System

A **stateful multi-agent workflow platform** built with LangGraph, FastAPI, and React. This is not a chatbot — it is a genuine orchestration system where a Supervisor agent coordinates specialized agents, tools, persistent memory, and human approval to complete complex tasks.

---

## Architecture Overview

```
                         INTERNET
                             │
                    ┌────────┴────────┐
                    │                 │
              React Frontend    FastAPI Backend
              (Render Static)   (Render Web Service)
                    │                 │
                    └────────┬────────┘
                             │ REST + polling
                             │
                    ┌────────┴────────────┐
                    │    FastAPI App       │
                    │                     │
                    │  LangGraph Engine   │
                    │  ┌──────────────┐   │
                    │  │  Supervisor  │   │
                    │  └──────┬───────┘   │
                    │  ┌──────┼───────┐   │
                    │  │      │       │   │
                    │  ▼      ▼       ▼   │
                    │  Res  Anal   Writer  │
                    │  │      │       │   │
                    │  └──Tools────────┘  │
                    │         │           │
                    │      Reviewer       │
                    │         │           │
                    │    [Approval?]      │
                    │         │           │
                    │      Finalize       │
                    └─────────────────────┘
                             │
                        PostgreSQL
                   (LangGraph checkpoints +
                    application state)
                             │
                         OpenRouter
                      (LLM provider)
```

---

## Why Multi-Agent Orchestration?

A standard LLM call is:

```
User → LLM → Answer
```

This system is:

```
User
 ↓
Supervisor Agent (orchestrator)
 ↓ routing decision
Researcher Agent → search tool → web_search → findings
 ↓
Analyst Agent → calculator tool → structured analysis
 ↓
Writer Agent → memory_search → formatted response
 ↓
Reviewer Agent → quality check → PASS or FAIL
 ↓ (if require_approval)
INTERRUPT → human decision → RESUME
 ↓
Finalize → PostgreSQL → Frontend
```

Each agent has a **defined role**, **authorized tools**, and **structured output format**. The Supervisor uses conditional routing — it does not blindly chain agents but reasons about what is needed at each step.

---

## LangGraph Architecture

### Why LangGraph?

LangGraph provides:
- **Explicit graph definition** — nodes, edges, conditional routing
- **Typed state** — `WorkflowState` TypedDict shared across all nodes
- **PostgreSQL checkpointing** — state persists across server restarts
- **interrupt() / Command(resume=...)** — genuine pause/resume for human-in-the-loop

### Graph Definition

```python
graph.add_node("supervisor", supervisor_node)
graph.add_node("researcher", researcher_node)
graph.add_node("analyst", analyst_node)
graph.add_node("writer", writer_node)
graph.add_node("reviewer", reviewer_node)
graph.add_node("approval", approval_node)   # interrupt() here
graph.add_node("finalize", finalize_node)
graph.add_node("failed", failed_node)

graph.add_edge(START, "supervisor")
graph.add_conditional_edges("supervisor", supervisor_router, {...})
graph.add_edge("researcher", "supervisor")  # always returns to supervisor
graph.add_edge("analyst", "supervisor")
graph.add_edge("writer", "supervisor")
graph.add_conditional_edges("reviewer", review_router, {...})
graph.add_conditional_edges("approval", approval_router, {...})
graph.add_edge("finalize", END)
graph.add_edge("failed", END)
```

### Workflow State

```python
class WorkflowState(TypedDict):
    thread_id: str           # LangGraph thread identifier
    user_id: str             # User isolation
    workflow_run_id: str     # DB record ID
    user_request: str        # Original task
    current_agent: str       # Who is executing now
    workflow_status: str     # running|paused|completed|failed
    messages: list[BaseMessage]        # Conversation history
    memory_context: Optional[str]      # Retrieved long-term memory
    research_results: Optional[dict]   # Researcher output
    analysis_results: Optional[dict]   # Analyst output
    draft: Optional[str]               # Writer output
    review_result: Optional[dict]      # Reviewer output
    final_response: Optional[str]      # Delivered to user
    tool_results: list[dict]           # All tool calls this run
    errors: list[dict]                 # Error history
    approval_status: Optional[str]     # pending|approved|rejected
    require_approval: bool             # User setting
    step_count: int                    # Current step
    max_steps: int                     # Hard limit (prevents loops)
    review_cycles: int                 # How many review loops ran
    max_review_cycles: int             # Hard limit
    retry_counts: dict[str, int]       # Per-agent retry tracking
    max_retries: int                   # Hard limit
    next_agent: Optional[str]          # Supervisor's routing decision
```

### How Conditional Edges Work

```python
def supervisor_router(state: WorkflowState) -> str:
    next_agent = state.get("next_agent", "end")
    if next_agent == "end":
        return "finalize"
    return next_agent  # "researcher"|"analyst"|"writer"|"reviewer"|...
```

The Supervisor LLM returns JSON: `{"next_agent": "researcher", "reasoning": "...", "instructions": "..."}`. This decision is read by the conditional edge function and routes execution accordingly.

---

## Agent Responsibilities

| Agent | Role | Tools |
|---|---|---|
| **Supervisor** | Orchestrates everything — routes, detects failures, controls flow | None |
| **Researcher** | Gathers factual information | search, datetime, calculator, memory_search |
| **Analyst** | Analyzes research, finds patterns | calculator, memory_search |
| **Writer** | Writes the final response from research + analysis | memory_search |
| **Reviewer** | Checks quality — returns pass or fail | None |

---

## Tool System

### Tool Registry

```python
AGENT_TOOLS = {
    "researcher": [web_search, get_current_datetime, calculator, memory_search],
    "analyst":    [calculator, memory_search],
    "writer":     [memory_search],
    "reviewer":   [],
    "supervisor": [],
}
```

### Tools

| Tool | Implementation | Safety |
|---|---|---|
| `calculator` | AST-based safe evaluator | No `eval()` — only allows arithmetic ops |
| `web_search` | DuckDuckGo (free, no API key) | No shell execution |
| `get_current_datetime` | Python `datetime.now(timezone.utc)` | Deterministic |
| `memory_search` | PostgreSQL ILIKE query | Scoped to current user |

---

## Memory System

### Short-term Memory
LangGraph's `WorkflowState.messages` — conversation history within a workflow run, preserved through PostgreSQL checkpoints.

### Long-term Memory
`memories` table in PostgreSQL. Stored explicitly, not by blindly saving every message.

```
Memory types:
- preference: "I prefer bullet points"
- outcome: "Last report on AI was well received"
- fact: "User works in fintech"
```

Memory flow:
1. User saves: `POST /api/memory {"content": "I prefer concise bullet points", "memory_type": "preference"}`
2. New workflow starts — `get_relevant_memories()` retrieves matching memories
3. Memory context is injected into `WorkflowState.memory_context`
4. Writer Agent calls `memory_search` tool and incorporates preferences
5. Output reflects user preferences — **demonstrably, not decoratively**

---

## Human-in-the-Loop

This uses LangGraph's real `interrupt()` mechanism — not a simulated flag.

```python
# approval.py (simplified)
async def approval_node(state: WorkflowState) -> dict:
    payload = {"action": "...", "reason": "...", ...}
    
    # Execution genuinely STOPS here.
    # LangGraph saves checkpoint to PostgreSQL.
    # The graph will not proceed until Command(resume=...) is called.
    decision = interrupt(payload)
    
    # This line only executes AFTER resume is called.
    return {"approval_status": decision}
```

Resume flow:
```python
# workflow_service.py
async def resume_workflow(thread_id: str, decision: str):
    async for event in graph.astream(
        Command(resume={"decision": decision}),
        config={"configurable": {"thread_id": thread_id}},
    ):
        ...
```

The workflow stays paused even across server restarts because the checkpoint is in PostgreSQL.

---

## Retry and Failure Recovery

Each agent tracks retries independently:

```python
retry_counts = dict(state.get("retry_counts", {}))
retry_counts["researcher"] = retry_counts.get("researcher", 0) + 1

if retry_counts["researcher"] < state.get("max_retries", 3):
    return {"errors": errors, "retry_counts": retry_counts, ...}  # supervisor re-routes
else:
    return {"research_results": empty_fallback, ...}  # continue with what we have
```

Guards against infinite loops:
- `max_steps` — absolute step limit
- `max_retries` — per-agent retry limit
- `max_review_cycles` — review loop limit (forced pass after N cycles)

---

## Database Schema

```sql
users               (id, email, hashed_password, created_at)
workflow_runs       (id, user_id, thread_id, task, status, current_agent,
                     step_count, max_steps, started_at, completed_at,
                     final_response, error_message, metadata)
workflow_events     (id, workflow_run_id, timestamp, agent_name, action,
                     tool_name, status, duration_ms, result_summary, error)
approvals           (id, workflow_run_id, thread_id, requesting_agent,
                     action_description, reason, risk_level, status,
                     created_at, decided_at)
memories            (id, user_id, content, memory_type, created_at, updated_at)
agent_executions    (id, workflow_run_id, agent_name, started_at,
                     completed_at, status, tool_calls_count, retry_count)
tool_executions     (id, workflow_run_id, tool_name, input_summary,
                     output_summary, status, duration_ms)
```

LangGraph also writes its own `checkpoints` table via `AsyncPostgresSaver`.

---

## API Endpoints

```
POST /api/auth/register          Create account
POST /api/auth/login             Get JWT token
GET  /api/auth/me                Current user

POST /api/workflows              Create + start workflow (BackgroundTask)
GET  /api/workflows              List user's workflows
GET  /api/workflows/metrics      Dashboard statistics
GET  /api/workflows/{id}         Get workflow + events
GET  /api/workflows/{id}/state   Raw LangGraph checkpoint state
DELETE /api/workflows/{id}       Cancel workflow

GET  /api/approvals              List approvals
POST /api/approvals/{id}/approve Approve (resumes workflow)
POST /api/approvals/{id}/reject  Reject (resumes workflow with rejection)

GET  /api/memory                 List user memories
POST /api/memory                 Create memory
PUT  /api/memory/{id}            Update memory
DELETE /api/memory/{id}          Delete memory

GET  /api/agents                 Agent stats (from real DB records)

GET  /health                     Liveness
GET  /health/ready               Readiness (checks DB + graph)
```

Interactive docs: `/docs` (FastAPI auto-generated)

---

## Frontend Pages

| Page | URL | Purpose |
|---|---|---|
| Dashboard | `/` | Live metrics, active workflows, pending approvals |
| New Task | `/tasks/new` | Task form with options |
| Workflow Detail | `/workflows/:id` | React Flow graph + live trace + final response |
| Approvals | `/approvals` | Review and approve/reject pending actions |
| Memory | `/memory` | CRUD for long-term memory |
| History | `/history` | All workflow runs |
| Agents | `/agents` | Agent cards with real execution statistics |

The Workflow Detail page polls `/api/workflows/:id` every 2 seconds while the workflow is active. The execution graph reflects actual state — nodes show pending/running/completed/failed/paused based on real `workflow_events` records.

---

## Deployment Architecture (Render)

```
render.yaml defines:

databases:
  - name: agent-orchestration-db     # Free PostgreSQL
    plan: free

services:
  - name: agent-orchestration-api   # Python web service
    buildCommand: pip install -r requirements.txt
    startCommand: alembic upgrade head && uvicorn ...

  - name: agent-orchestration-ui    # Static site
    buildCommand: npm ci && npm run build
    staticPublishPath: dist
```

### Free-Tier Design Decisions

| Constraint | Mitigation |
|---|---|
| Services sleep after 15 min | All state in PostgreSQL; workflows resume from checkpoint |
| Ephemeral filesystem | Nothing stored locally; PostgreSQL only |
| No persistent worker process | Workflows run as `FastAPI BackgroundTask` in-process |
| 512MB RAM limit | No vector DB; simple PostgreSQL memory search |
| 90-day PostgreSQL expiry | Environment variable for re-provision |

---

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 15+ (or Docker)
- OpenRouter API key

### Using Docker Compose

```bash
cp .env.example .env
# Edit .env — set OPENROUTER_API_KEY and SECRET_KEY

docker compose up --build
```

Frontend: http://localhost:3000  
Backend API: http://localhost:8000  
API Docs: http://localhost:8000/docs

### Without Docker

```bash
# Start PostgreSQL
# Create database: orchestration

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp ../.env.example .env     # configure DATABASE_URL and OPENROUTER_API_KEY
python -m alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | asyncpg PostgreSQL URL | required |
| `SYNC_DATABASE_URL` | psycopg PostgreSQL URL (for Alembic) | required |
| `LLM_PROVIDER` | `openrouter` or `ollama` | `openrouter` |
| `LLM_MODEL` | Model identifier | `meta-llama/llama-3.1-8b-instruct:free` |
| `OPENROUTER_API_KEY` | OpenRouter API key | required for OpenRouter |
| `SECRET_KEY` | JWT signing key | required in production |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173` |
| `MAX_WORKFLOW_STEPS` | Max graph steps per workflow | `20` |
| `MAX_RETRIES` | Max retries per agent | `3` |
| `MAX_REVIEW_CYCLES` | Max reviewer loops | `3` |

---

## Testing

```bash
cd backend

# Unit tests (no DB required)
pytest tests/unit/ -v

# Integration tests (requires DB)
TEST_DATABASE_URL=postgresql+asyncpg://... pytest tests/integration/ -v

# E2E scenario tests (state machine logic — no LLM required)
pytest tests/e2e/ -v

# All tests
pytest -v --cov=app --cov-report=html
```

### Test Coverage

- **Unit**: calculator safety, routing logic, auth, datetime tool
- **Integration**: register/login, workflow CRUD, memory CRUD, user isolation
- **E2E**: 5 demonstration scenarios verified at state machine level

---

## Example Workflow: AI Research Report

1. User submits: *"Research the current state of quantum computing and prepare a structured report"*
2. `POST /api/workflows` → returns workflow ID immediately
3. BackgroundTask starts graph execution:
   - Supervisor → routes to Researcher
   - Researcher → calls `web_search("quantum computing 2024 advances")` × 3
   - Researcher → returns structured findings
   - Supervisor → routes to Analyst
   - Analyst → calls `calculator("(number of qubits) / (error rate)")` for analysis
   - Analyst → returns key points and conclusion
   - Supervisor → routes to Writer
   - Writer → calls `memory_search("report format preferences")` — finds "use bullet points"
   - Writer → produces formatted report with bullet points (memory influenced output)
   - Supervisor → routes to Reviewer
   - Reviewer → PASS
   - Supervisor → end
   - Finalize → saves final_response to DB
4. Frontend polls, shows live execution trace, then displays final response

Execution trace visible on `/workflows/:id`:
```
14:32:01 supervisor   START
14:32:02 supervisor   → researcher
14:32:03 researcher   web_search   SUCCESS  2341ms
14:32:06 researcher   web_search   SUCCESS  1890ms
14:32:08 researcher   COMPLETE
14:32:09 supervisor   → analyst
14:32:12 analyst      calculator   SUCCESS  12ms
14:32:14 analyst      COMPLETE
14:32:15 supervisor   → writer
14:32:19 writer       memory_search SUCCESS  45ms
14:32:24 writer       COMPLETE
14:32:25 supervisor   → reviewer
14:32:28 reviewer     PASS
14:32:28 supervisor   → end
14:32:28 finalize     COMPLETE
```

---

## Limitations

1. **Free LLM models** may produce less reliable structured JSON — the system handles this with fallback parsing and retry logic.
2. **Render free-tier sleep** causes cold starts (30-60s delay after inactivity).
3. **No vector search** — memory retrieval uses keyword matching. Semantic search (pgvector) would improve relevance.
4. **Single process** — BackgroundTasks run in the same process as FastAPI. Under load, a separate worker (e.g., Celery + Redis) would be more robust.
5. **No streaming** — frontend polls every 2 seconds; Server-Sent Events would enable true real-time updates.

---

## Future Improvements

- **pgvector** for semantic memory search
- **Streaming responses** via SSE
- **Tool expansion**: code execution sandbox, file upload, chart generation
- **Agent specialization**: add domain-specific agents (legal, medical, financial)
- **Workflow templates**: pre-built graphs for common tasks
- **Multi-user collaboration**: shared workflows, team approvals
- **Cost tracking**: per-workflow LLM token usage
- **Webhook notifications**: alert users when workflows complete or need approval

---

## Design Decisions

**Why LangGraph and not a simple sequential chain?**
Sequential chains cannot handle conditional routing, retries, human interrupts, or resumption from persisted state. LangGraph exposes the graph structure explicitly — I can explain every node, edge, and routing decision.

**Why PostgreSQL and not Redis for checkpoints?**
Redis is not available on Render's free tier. PostgreSQL provides durable checkpoints and application state in a single free-tier resource. The `langgraph-checkpoint-postgres` package makes this straightforward.

**Why polling and not WebSockets?**
WebSockets require a persistent connection that conflicts with Render's free-tier sleep behavior. Polling every 2 seconds provides adequate UX for a portfolio system without the infrastructure complexity.

**Why BackgroundTasks and not a separate worker?**
A separate worker (Celery, ARQ) requires a message broker (Redis, RabbitMQ) — neither is available on Render's free tier. FastAPI's `BackgroundTasks` run in the same process and work reliably for this use case.

**Why DuckDuckGo for search?**
Free, no API key required, returns real results. The search tool is abstracted behind an interface — swapping to SerpAPI or Tavily requires only changing the `_duckduckgo_search` implementation.
