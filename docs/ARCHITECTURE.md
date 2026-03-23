# Research Agent Backend Architecture

## Overview

FastAPI backend for a Research Agent that accepts a topic, decomposes it into sub-questions via Claude (tool use), searches per sub-question with Tavily, synthesizes a report, and streams progress to the frontend.

---

## 1. API Design

### Routes

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/research` | Start research job (returns job ID immediately) |
| `GET` | `/api/v1/research/{job_id}/stream` | **SSE stream** of progress events |
| `GET` | `/api/v1/research/{job_id}` | Poll final state (optional fallback) |
| `GET` | `/health` | Liveness probe |

**Design choice: Job + Stream separation**

- `POST /research` returns `{ job_id: string }` immediately. Client then opens SSE to `/research/{job_id}/stream`.
- Rationale: Clean separation of job creation vs. streaming; allows retries of stream without re-running research; supports future job queue / persistence.

### Request Schemas

```python
# POST /api/v1/research
class ResearchRequest(BaseModel):
    topic: str  # Required; max length e.g. 500
    max_subquestions: int | None = 5  # Optional cap
    search_depth: str | None = "basic"  # Tavily: basic | advanced
```

### Response Schemas

```python
# POST /api/v1/research → 202 Accepted
class ResearchJobResponse(BaseModel):
    job_id: str
    stream_url: str  # e.g. /api/v1/research/{job_id}/stream

# GET /api/v1/research/{job_id} → 200 OK (when complete)
class ResearchResultResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    topic: str
    sub_questions: list[str] | None
    report: str | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None
```

---

## 2. Streaming: SSE vs WebSocket

### Recommendation: **SSE (Server-Sent Events)**

| Criterion | SSE | WebSocket |
|-----------|-----|-----------|
| Direction | Server → Client only | Bidirectional |
| Protocol | HTTP; auto-reconnect | Custom; manual reconnect |
| Browser support | `EventSource` built-in | `WebSocket` API |
| Load balancers / proxies | Standard HTTP; no special config | May need upgrade handling |
| Complexity | Lower | Higher |
| Use case fit | Progress push, no client→server mid-stream | Chat, games, real-time collaboration |

**Justification**

- Research flow is **unidirectional**: server pushes status/search/report events; client does not need to send messages mid-stream.
- SSE is simpler to implement and operate (no upgrade handshake, no frame protocol).
- `EventSource` handles reconnection and `Last-Event-ID` automatically.
- FastAPI supports SSE via `StreamingResponse` with `text/event-stream`.
- If future needs require client→server during stream (e.g. "cancel", "refine"), a separate `POST /research/{job_id}/cancel` endpoint suffices.

**When to consider WebSocket**

- If you add interactive refinement (user sends follow-up questions during synthesis).
- If you need binary or very high-frequency updates.

---

## 3. Event Types for Streaming

All events are JSON objects sent as SSE `data` payloads. Include `event` and `timestamp` for every message.

| Event Type | When Emitted | Payload Shape |
|------------|--------------|---------------|
| `status` | Phase transitions | `{ event, timestamp, phase, message }` |
| `subquestion_generated` | After Claude returns each sub-question | `{ event, timestamp, index, sub_question, total }` |
| `search_started` | Before Tavily call per sub-question | `{ event, timestamp, sub_question_index, sub_question }` |
| `search_result` | After each Tavily result | `{ event, timestamp, sub_question_index, result_index, title, url, snippet }` |
| `synthesis_started` | Before final Claude synthesis | `{ event, timestamp }` |
| `final_report` | Report complete | `{ event, timestamp, report }` |
| `error` | Any failure | `{ event, timestamp, message, phase }` |

**Example SSE stream**

```
event: status
data: {"event":"status","timestamp":"2025-03-16T10:00:00Z","phase":"decomposing","message":"Decomposing topic into sub-questions"}

event: subquestion_generated
data: {"event":"subquestion_generated","timestamp":"...","index":0,"sub_question":"What is X?","total":3}

event: search_started
data: {"event":"search_started","timestamp":"...","sub_question_index":0,"sub_question":"What is X?"}

event: search_result
data: {"event":"search_result","timestamp":"...","sub_question_index":0,"result_index":0,"title":"...","url":"...","snippet":"..."}

event: synthesis_started
data: {"event":"synthesis_started","timestamp":"..."}

event: final_report
data: {"event":"final_report","timestamp":"...","report":"# Research Report\n\n..."}

event: done
data: {"event":"done","timestamp":"..."}
```

---

## 4. Concurrency and Ordering

### Approach: `asyncio.gather` with Rate Limiting

- **Decomposition**: Single Claude call with tool use → returns ordered list of sub-questions.
- **Search**: Run Tavily searches in parallel via `asyncio.gather` for all sub-questions.
- **Rate limiting**: Use a semaphore or token-bucket to cap concurrent Tavily requests (e.g. 3–5) to avoid 429s.
- **Ordering**: Emit events in a deterministic order:
  1. All `subquestion_generated` in index order (from Claude response).
  2. For each sub-question, emit `search_started` then `search_result`(s) in order.
  3. `synthesis_started` → `final_report` → `done`.

**Implementation sketch**

- Use `asyncio.Queue` or a callback-based `AsyncGenerator` that the orchestrator pushes events into.
- Search phase: `gather` with a shared `asyncio.Semaphore(3)`; each task yields `search_started` → N×`search_result` → (implicit completion).
- To preserve sub-question order: process results by index; emit `search_result` events in (sub_question_index, result_index) order even if tasks complete out of order (buffer and flush when prior indices are done).

### Alternative: Sequential Search

- Simpler: run searches one-by-one. No rate-limit logic, trivial ordering.
- Trade-off: Slower; use only if Tavily limits are very strict.

---

## 5. Observability

### Logging

- **Structured JSON logs** (e.g. `structlog` or `python-json-logger`).
- Fields: `timestamp`, `level`, `message`, `job_id`, `request_id`, `phase`, `duration_ms`.
- Log at phase boundaries, API calls (Claude, Tavily), and errors.

### Request IDs

- Generate `request_id` (UUID) per HTTP request; pass via middleware.
- Include in all log lines and optionally in SSE event payloads (`request_id`, `job_id`).
- Return `X-Request-ID` in response headers for correlation.

### Metrics (Optional)

- Counters: `research_jobs_started`, `research_jobs_completed`, `research_jobs_failed`.
- Histograms: `research_duration_seconds`, `claude_latency_seconds`, `tavily_latency_seconds`.
- Expose via `/metrics` (Prometheus) if needed.

---

## 6. Config and Secrets

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Claude API | `sk-ant-...` |
| `TAVILY_API_KEY` | Tavily search | `tvly-...` |
| `CLAUDE_MODEL` | Model name | `claude-sonnet-4-6-20250514` |
| `TAVILY_SEARCH_DEPTH` | basic / advanced | `basic` |
| `MAX_CONCURRENT_SEARCHES` | Semaphore size | `3` |
| `LOG_LEVEL` | Logging | `INFO` |
| `ENVIRONMENT` | dev / staging / prod | `dev` |

### Loading

- Use `pydantic-settings` (or `pydantic` v2 `BaseSettings`) to load from env.
- Validate on startup; fail fast if required keys missing.
- Never log or expose API keys.

---

## 7. Project Structure

```
research-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, middleware, routes
│   ├── config.py               # Pydantic settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py       # /research, /research/{id}, /research/{id}/stream
│   │   │   └── schemas.py      # Request/response models
│   │   └── deps.py             # Depends(): config, request_id
│   ├── services/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Top-level research flow
│   │   ├── claude_service.py   # Anthropic API, tool use
│   │   ├── tavily_service.py   # Tavily search
│   │   └── events.py           # Event types, serialization
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── request_id.py       # Inject X-Request-ID
│   │   └── logging.py          # Request logging
│   └── utils/
│       ├── __init__.py
│       └── sse.py              # SSE formatting helpers
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   └── test_services.py
├── docs/
│   └── ARCHITECTURE.md         # This file
├── .env.example
├── pyproject.toml              # or requirements.txt
└── README.md
```

### Key Interfaces

- **Orchestrator**: `async def run_research(topic: str, event_queue: AsyncQueue) -> None` — drives decomposition → search → synthesis, pushes events to queue.
- **Claude service**: `async def decompose_topic(topic: str) -> list[str]`; `async def synthesize_report(sub_questions: list[str], search_results: dict[int, list[SearchResult]]) -> str`.
- **Tavily service**: `async def search(query: str, depth: str) -> list[SearchResult]`.
- **SSE route**: Consumes from `event_queue` (or equivalent) and yields `StreamingResponse` with `text/event-stream`.

---

## 8. Error Handling

- **Claude/Tavily failures**: Emit `error` event, set job status to `failed`, include `error` in final response.
- **Stream disconnect**: Log; job may continue in background; client can reconnect to stream (if you persist events) or poll `/research/{id}`.
- **Validation errors**: 422 with Pydantic error body.
- **Missing job**: 404.

---

## 9. Summary

| Decision | Choice |
|----------|--------|
| Streaming | SSE |
| Job model | POST returns job_id; GET stream for events |
| Concurrency | `asyncio.gather` + semaphore for Tavily |
| Ordering | Deterministic event emission by index |
| Config | Pydantic settings from env |
| Observability | Structured logs, request_id, optional metrics |
| Structure | `app/` with api, services, middleware, utils |
