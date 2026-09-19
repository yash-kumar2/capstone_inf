from __future__ import annotations

from fastapi import FastAPI

from .settings import SETTINGS

app = FastAPI(title="AI Invoice Auditor Agent")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "postgres": SETTINGS["POSTGRES_DB"],
        "redis": SETTINGS["REDIS_HOST"],
        "qdrant": SETTINGS["QDRANT_HOST"],
    }
