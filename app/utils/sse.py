from __future__ import annotations

import json
from typing import Any, Literal


SseEventName = Literal[
    "status",
    "subquestion_generated",
    "search_started",
    "search_result",
    "synthesis_started",
    "final_report",
    "error",
    "done",
]


def sse_format(event: SseEventName, data: dict[str, Any]) -> str:
    # SSE format: "event: <name>\n" + "data: <json>\n\n"
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"

