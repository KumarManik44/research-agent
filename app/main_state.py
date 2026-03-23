from __future__ import annotations

import asyncio
from dataclasses import dataclass

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.claude_service import ClaudeClient
from app.services.orchestrator import JobState, ResearchOrchestrator
from app.services.tavily_service import TavilyClient


@dataclass
class JobParams:
    max_subquestions: int
    search_depth: str
    max_results: int


class JobStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._jobs: dict[str, JobState] = {}

        claude = ClaudeClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
        tavily = TavilyClient(api_key=settings.tavily_api_key, timeout_seconds=settings.tavily_timeout_seconds)
        self._orch = ResearchOrchestrator(
            claude=claude,
            tavily=tavily,
            max_concurrent_searches=settings.max_concurrent_searches,
            default_depth=settings.tavily_search_depth,
            default_max_results=settings.tavily_max_results,
        )

        self._tasks: dict[str, asyncio.Task[None]] = {}

    def create_job(self, *, topic: str) -> JobState:
        job = self._orch.new_job(topic)
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> JobState | None:
        return self._jobs.get(job_id)

    def start_job(self, job_id: str, *, max_subquestions: int, search_depth: str, max_results: int) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job_id in self._tasks:
            return

        async def runner() -> None:
            await self._orch.run(
                job,
                max_subquestions=max_subquestions,
                search_depth=search_depth,
                max_results=max_results,
            )

        self._tasks[job_id] = asyncio.create_task(runner())


_store: JobStore | None = None


def get_job_store(settings: Settings = Depends(get_settings)) -> JobStore:
    global _store
    if _store is None:
        _store = JobStore(settings)
    return _store