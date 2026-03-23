# 🔍 Research Agent

An autonomous AI research agent that decomposes a topic into sub-questions, executes parallel web searches, and synthesizes a fully cited Markdown report — streamed live to the UI via SSE.

Built as a demonstration of **agentic tool-use loops**, **LLM function calling**, and **real-time async streaming** in a production-grade full-stack architecture.

---

## 🧠 What Makes This Agentic?

Most AI apps are single-turn: you ask, it answers. This agent operates in a **multi-step reasoning loop**:

1. **Decompose** — Gemini 2.5 Flash receives the topic and autonomously breaks it into 3–7 focused sub-questions
2. **Search** — For each sub-question, the LLM calls the `tavily_search` tool via native function calling
3. **Read** — Search results are fed back into the LLM's context as tool responses
4. **Synthesize** — The LLM continues the loop until it has enough information, then writes a structured report with inline citations
5. **Stream** — Every step (decomposing, searching, synthesizing) is streamed live to the frontend via SSE

The LLM decides **when to search**, **what to search for**, and **when it has enough information** — that's what makes it an agent, not just a chatbot.

---

## 🛠 Tech Stack

| Layer | Technology | Role |
|---|---|---|
| LLM | Google Gemini 2.5 Flash | Reasoning, tool-use, report synthesis |
| Search | Tavily Search API | Real-time web search tool |
| Backend | FastAPI (async) | Job management, SSE streaming |
| Frontend | React + Vite + Tailwind | Live progress feed, report rendering |
| Streaming | Server-Sent Events (SSE) | Real-time agent progress to UI |

---

## 🏗 Architecture

```
User Input (topic)
      │
      ▼
FastAPI — POST /api/v1/research
      │   creates async Job
      ▼
ResearchOrchestrator
      │
      ▼
ClaudeClient.run_tool_loop()         ← Gemini 2.5 Flash
      │
      ├── LLM calls tavily_search("sub-question 1")
      │         └── TavilyClient.search() → results fed back as tool response
      │
      ├── LLM calls tavily_search("sub-question 2")
      │         └── ... (up to MAX_CONCURRENT_SEARCHES in parallel)
      │
      └── LLM returns final Markdown report with citations
      │
      ▼
SSE Stream — GET /api/v1/research/{job_id}/stream
      │
      ▼
React Frontend
  ├── Live progress feed (decomposing → searching → synthesizing)
  └── Final report rendered as Markdown with clickable citations
```

**Key architectural decisions:**
- **Swappable LLM backend** — `ClaudeClient` is an abstraction layer. The orchestrator has zero knowledge of which LLM is running underneath, making it trivial to swap models
- **Async job queue** — Each research job runs as an `asyncio.Task`, allowing multiple concurrent jobs without blocking
- **SSE over WebSockets** — One-way streaming is sufficient here; SSE is simpler, HTTP-native, and auto-reconnects

---

## ✨ Features

- 🔄 **Agentic loop** — LLM autonomously decides when and what to search
- ⚡ **Live streaming** — Watch the agent think in real time via SSE
- 📑 **Cited reports** — Every claim is backed by a numbered source
- 🔀 **Concurrent search** — Multiple sub-questions searched in parallel
- 🔌 **Swappable LLM** — Gemini, Claude, or any model with tool-use support

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Gemini API key](https://aistudio.google.com) (free tier)
- [Tavily API key](https://app.tavily.com) (free tier)

### 1. Clone the repo

```bash
git clone https://github.com/KumarManik44/research-agent.git
cd research-agent
```

### 2. Backend setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY and TAVILY_API_KEY to .env
```

### 3. Run the backend

```bash
source venv/bin/activate
export $(cat .env | grep -v '#' | xargs)
./venv/bin/uvicorn app.main:app --reload --port 8000
```

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) and enter any research topic.

---

## 📡 API Reference

### Start a research job

```
POST /api/v1/research
```

```json
{
  "topic": "Impact of AI in Healthcare in 2025",
  "max_subquestions": 6,
  "search_depth": "basic",
  "max_results": 5
}
```

### Stream progress (SSE)

```
GET /api/v1/research/{job_id}/stream
```

| Event | Payload |
|---|---|
| `status` | `{ phase, message }` |
| `search_started` | `{ query }` |
| `search_result` | `{ citation_id, title, url, snippet }` |
| `synthesis_started` | `{}` |
| `final_report` | `{ report }` |
| `done` | `{}` |

---

## 📁 Project Structure

```
research-agent/
├── app/
│   ├── api/v1/
│   │   ├── routes.py            # FastAPI endpoints
│   │   └── schemas.py           # Request/response models
│   ├── services/
│   │   ├── claude_service.py    # Gemini client + tool-use loop
│   │   ├── orchestrator.py      # Agentic research loop
│   │   └── tavily_service.py    # Tavily search client
│   ├── config.py                # Pydantic settings
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/          # TopicInput, ProgressFeed, ReportView
│       └── hooks/               # useResearchStream (SSE)
├── docs/                        # Architecture documentation
└── requirements.txt
```

---

## 📄 License

MIT
