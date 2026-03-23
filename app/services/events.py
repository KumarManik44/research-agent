from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


EventType = Literal[
    "status",
    "subquestion_generated",
    "search_started",
    "search_result",
    "synthesis_started",
    "final_report",
    "error",
    "done",
]


class Event(BaseModel):
    event: EventType
    timestamp: str = Field(default_factory=utc_now_iso)
    data: dict[str, Any] = Field(default_factory=dict)

