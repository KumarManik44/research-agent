from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.v1.routes import router as v1_router


def create_app() -> FastAPI:
    # Do not require API keys at import/startup time. Keys are only required
    # when calling the research endpoints.
    logging.basicConfig(level=logging.INFO)

    app = FastAPI(title="Research Agent Backend", version="0.1.0")
    app.include_router(v1_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

