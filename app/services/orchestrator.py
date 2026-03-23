from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from app.services.claude_service import ClaudeClient, ToolDef, ToolUse
from app.services.events import Event
from app.services.tavily_service import TavilyClient, TavilyResult


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobState:
    job_id: str
    topic: str
    status: str = "pending"  # pending|running|completed|failed
    created_at: datetime = field(default_factory=now_utc)
    completed_at: datetime | None = None
    sub_questions: list[str] | None = None
    report: str | None = None
    error: str | None = None
    queue: asyncio.Queue[Event] = field(default_factory=asyncio.Queue)


SYSTEM_PROMPT = """You are a Research Agent that produces well-sourced, structured reports.

Workflow:
1) Break the topic into specific, non-overlapping sub-questions (3–7).
2) For each sub-question, use the tavily_search tool to gather sources.
3) Synthesize a structured Markdown report with inline numbered citations like [1], [2].
4) End with a ## References section mapping each citation number to exactly one URL.

Citation rules:
- Every factual claim must have at least one citation.
- Only cite URLs returned by the tavily_search tool.
- Reuse the same number for the same URL across the report.
"""


def build_user_prompt(topic: str, *, max_subquestions: int) -> str:
    return f"""Research the following topic and produce a structured Markdown report with citations.

Topic: {topic}

Constraints:
- Use at most {max_subquestions} sub-questions.
- Prefer recent, primary, and authoritative sources when available.

Now proceed with the workflow. You must use tavily_search for each sub-question.
"""


class ResearchOrchestrator:
    def __init__(
        self,
        *,
        claude: ClaudeClient,
        tavily: TavilyClient,
        max_concurrent_searches: int = 3,
        default_depth: str = "basic",
        default_max_results: int = 5,
    ) -> None:
        self._claude = claude
        self._tavily = tavily
        self._sem = asyncio.Semaphore(max_concurrent_searches)
        self._default_depth = default_depth
        self._default_max_results = default_max_results

    def new_job(self, topic: str) -> JobState:
        return JobState(job_id=str(uuid.uuid4()), topic=topic)

    async def run(self, job: JobState, *, max_subquestions: int, search_depth: str, max_results: int) -> None:
        job.status = "running"
        await job.queue.put(Event(event="status", data={"phase": "decomposing", "message": "Decomposing topic"}))

        tools = [
            ToolDef(
                name="tavily_search",
                description="Search the web using the Tavily API and return results with title, url, content snippet, and score.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (1-20)",
                            "minimum": 1,
                            "maximum": 20,
                            "default": max_results,
                        },
                        "search_depth": {
                            "type": "string",
                            "description": "basic or advanced",
                            "enum": ["basic", "advanced"],
                            "default": search_depth,
                        },
                    },
                    "required": ["query"],
                },
            )
        ]

        # Keep stable citation numbering by assigning IDs centrally as results arrive.
        citation_url_to_id: dict[str, int] = {}
        next_citation_id = 1

        async def tool_handler(tu: ToolUse) -> Any:
            nonlocal next_citation_id
            if tu.name != "tavily_search":
                return {"error": f"Unknown tool: {tu.name}"}

            query = str(tu.input.get("query") or "").strip()
            depth = str(tu.input.get("search_depth") or search_depth)
            mr = int(tu.input.get("max_results") or max_results)

            await job.queue.put(Event(event="search_started", data={"query": query}))

            async with self._sem:
                results = await self._tavily.search(query=query, max_results=mr, search_depth=depth)

            packed: list[dict[str, Any]] = []
            for r in results:
                url = r.url
                if url and url not in citation_url_to_id:
                    citation_url_to_id[url] = next_citation_id
                    next_citation_id += 1
                cid = citation_url_to_id.get(url)

                await job.queue.put(
                    Event(
                        event="search_result",
                        data={
                            "citation_id": cid,
                            "title": r.title,
                            "url": r.url,
                            "snippet": r.content[:400],
                            "score": r.score,
                        },
                    )
                )

                packed.append(
                    {
                        "citation_id": cid,
                        "title": r.title,
                        "url": r.url,
                        "content": r.content,
                        "score": r.score,
                    }
                )

            return {"query": query, "results": packed}

        try:
            await job.queue.put(Event(event="status", data={"phase": "searching", "message": "Searching sources"}))
            report = await self._claude.run_tool_loop(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(job.topic, max_subquestions=max_subquestions),
                tools=tools,
                on_tool_use=tool_handler,
            )

            await job.queue.put(Event(event="synthesis_started", data={}))
            job.report = report
            job.status = "completed"
            job.completed_at = now_utc()
            await job.queue.put(Event(event="final_report", data={"report": report}))
            await job.queue.put(Event(event="done", data={}))
        except Exception as e:
            job.status = "failed"
            job.completed_at = now_utc()
            job.error = str(e)
            await job.queue.put(Event(event="error", data={"message": job.error}))
            await job.queue.put(Event(event="done", data={}))

