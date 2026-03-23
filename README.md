# Research Agent (FastAPI backend)

FastAPI backend that accepts a research topic, uses **Claude `claude-sonnet-4-6`** with **tool use** to call **Tavily search**, and streams progress + the final cited Markdown report via **SSE**.

## Setup

1) Create a virtualenv and install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Configure environment:

```bash
cp .env.example .env
# edit .env with your keys
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## API

### Start a job

`POST /api/v1/research`

Body:

```json
{
  "topic": "Latest estimated population of Bhopal (2024-2026)",
  "max_subquestions": 6,
  "search_depth": "basic",
  "max_results": 5
}
```

Response:

```json
{ "job_id": "...", "stream_url": "/api/v1/research/.../stream" }
```

### Stream progress (SSE)

`GET /api/v1/research/{job_id}/stream`

Frontend example:

```js
const es = new EventSource(`/api/v1/research/${jobId}/stream`);
es.addEventListener("search_result", (e) => console.log(JSON.parse(e.data)));
es.addEventListener("final_report", (e) => console.log(JSON.parse(e.data).report));
es.addEventListener("done", () => es.close());
```

### Poll final state (optional)

`GET /api/v1/research/{job_id}`

