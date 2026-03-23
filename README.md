# 🔍 Research Agent

An autonomous AI research agent that takes a topic, searches the web, and produces a structured, cited Markdown report — all streamed live to the UI.

Built with **Gemini 2.5 Flash** + **Tavily Search** + **FastAPI** + **React**.

![Research Agent Demo]

---

## ✨ How It Works

1. You enter a research topic
2. The agent autonomously breaks it into sub-questions
3. Each sub-question is searched via Tavily's web search API
4. Gemini 2.5 Flash synthesizes the results into a structured report
5. Progress streams live to the frontend via SSE — you watch it think in real time

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| LLM | Google Gemini 2.5 Flash (tool use / function calling) |
| Search | Tavily Search API |
| Backend | FastAPI + SSE streaming |
| Frontend | React + Vite + Tailwind CSS |
| Architecture | Agentic loop — plan → search → synthesize |

---

## 🚀 Getting Started

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
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Get your keys here:
- Gemini: [aistudio.google.com](https://aistudio.google.com) — free tier available
- Tavily: [app.tavily.com](https://app.tavily.com) — free tier available

### 4. Run the backend

```bash
source venv/bin/activate
export $(cat .env | grep -v '#' | xargs)
./venv/bin/uvicorn app.main:app --reload --port 8000
```

### 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) and start researching.

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

Returns:

```json
{ "job_id": "...", "stream_url": "/api/v1/research/.../stream" }
```

### Stream progress (SSE)

```
GET /api/v1/research/{job_id}/stream
```

Events: `status` → `search_started` → `search_result` → `synthesis_started` → `final_report` → `done`

### Get job state

```
GET /api/v1/research/{job_id}
```

---

## 📁 Project Structure

```
research-agent/
├── app/
│   ├── api/v1/          # FastAPI routes
│   ├── services/
│   │   ├── claude_service.py    # Gemini client + tool-use loop
│   │   ├── orchestrator.py      # Agentic research loop
│   │   └── tavily_service.py    # Tavily search client
│   ├── config.py
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/  # TopicInput, ProgressFeed, ReportView
│       └── hooks/       # useResearchStream (SSE)
├── docs/                # Architecture docs
└── requirements.txt
```

---

## 📄 License

MIT
