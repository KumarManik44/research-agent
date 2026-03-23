from __future__ import annotations

import os
import sys
from typing import Any

from anthropic import Anthropic


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Export it or put it in your .env and run via your shell."
        )
    return key


def _safe_get(obj: Any, key: str, default: str = "") -> str:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return str(obj.get(key, default))
    return str(getattr(obj, key, default))


def main() -> int:
    api_key = _get_api_key()
    client = Anthropic(api_key=api_key)

    try:
        # Anthropic Python SDK: list available models for this key/account.
        page = client.models.list()
    except Exception as e:
        print(f"Failed to list models: {e}", file=sys.stderr)
        return 1

    data = getattr(page, "data", None) or []
    if not data:
        print("No models returned (empty list).")
        return 0

    # Print a readable table
    rows: list[tuple[str, str, str]] = []
    for m in data:
        model_id = _safe_get(m, "id")
        display_name = _safe_get(m, "display_name")
        created_at = _safe_get(m, "created_at")
        rows.append((model_id, display_name, created_at))

    rows.sort(key=lambda r: r[0])

    col1 = max(len("id"), max(len(r[0]) for r in rows))
    col2 = max(len("display_name"), max(len(r[1]) for r in rows))
    col3 = max(len("created_at"), max(len(r[2]) for r in rows))

    print(f"{'id'.ljust(col1)}  {'display_name'.ljust(col2)}  {'created_at'.ljust(col3)}")
    print(f"{'-' * col1}  {'-' * col2}  {'-' * col3}")
    for r in rows:
        print(f"{r[0].ljust(col1)}  {r[1].ljust(col2)}  {r[2].ljust(col3)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

