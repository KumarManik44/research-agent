from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class TavilyResult:
    title: str
    url: str
    content: str
    score: float | None = None


class TavilyClient:
    def __init__(self, api_key: str, *, timeout_seconds: int = 20) -> None:
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)

    async def search(
        self,
        *,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
    ) -> list[TavilyResult]:
        # https://docs.tavily.com/ (Search endpoint)
        url = "https://api.tavily.com/search"
        payload: dict[str, Any] = {
            "api_key": self._api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": False,
        }

        retries = 3
        backoff = 2.0
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload)
                if resp.status_code in (401, 403):
                    resp.raise_for_status()
                if resp.status_code == 429:
                    raise httpx.HTTPStatusError("Rate limited", request=resp.request, response=resp)
                resp.raise_for_status()
                data = resp.json()
                results: list[TavilyResult] = []
                for r in data.get("results", []) or []:
                    results.append(
                        TavilyResult(
                            title=str(r.get("title") or ""),
                            url=str(r.get("url") or ""),
                            content=str(r.get("content") or ""),
                            score=(float(r["score"]) if "score" in r and r["score"] is not None else None),
                        )
                    )
                return results
            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code if e.response is not None else None
                if status in (401, 403):
                    raise
                if status == 429 or (status is not None and 500 <= status <= 599):
                    if attempt < retries:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                raise
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_exc = e
                if attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise

        if last_exc:
            raise last_exc
        return []

