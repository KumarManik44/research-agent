from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.v1.schemas import ResearchJobResponse, ResearchRequest, ResearchResultResponse
from app.config import Settings, get_settings
from app.main_state import JobStore, get_job_store
from app.services.events import Event, utc_now_iso
from app.utils.sse import sse_format


router = APIRouter(prefix="/api/v1")


@router.post("/research", response_model=ResearchJobResponse, status_code=202)
async def start_research(
    req: ResearchRequest,
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
) -> ResearchJobResponse:
    job = store.create_job(topic=req.topic)

    max_subq = req.max_subquestions or settings.max_subquestions
    depth = req.search_depth or settings.tavily_search_depth
    max_results = req.max_results or settings.tavily_max_results

    store.start_job(job.job_id, max_subquestions=max_subq, search_depth=depth, max_results=max_results)
    return ResearchJobResponse(job_id=job.job_id, stream_url=f"/api/v1/research/{job.job_id}/stream")


@router.get("/research/{job_id}", response_model=ResearchResultResponse)
async def get_research(job_id: str, store: JobStore = Depends(get_job_store)) -> ResearchResultResponse:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return ResearchResultResponse(
        job_id=job.job_id,
        status=job.status,  # type: ignore[arg-type]
        topic=job.topic,
        sub_questions=job.sub_questions,
        report=job.report,
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/research/{job_id}/stream")
async def stream_research(job_id: str, request: Request, store: JobStore = Depends(get_job_store)) -> StreamingResponse:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    async def gen() -> AsyncGenerator[str, None]:
        # Initial ping to open the stream
        yield sse_format("status", {"event": "status", "timestamp": utc_now_iso(), "phase": "connected"})

        while True:
            if await request.is_disconnected():
                break

            try:
                ev: Event = await asyncio.wait_for(job.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            payload = {"event": ev.event, "timestamp": ev.timestamp, **ev.data}
            yield sse_format(ev.event, payload)  # type: ignore[arg-type]

            if ev.event == "done":
                break

    return StreamingResponse(gen(), media_type="text/event-stream")

