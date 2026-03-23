from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)
    max_subquestions: int | None = Field(default=None, ge=1, le=12)
    search_depth: Literal["basic", "advanced"] | None = Field(default=None)
    max_results: int | None = Field(default=None, ge=1, le=20)


class ResearchJobResponse(BaseModel):
    job_id: str
    stream_url: str


class ResearchResultResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    topic: str
    sub_questions: list[str] | None = None
    report: str | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

