import os
from typing import Any


REQUIRED_VARS = [
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "REDIS_HOST",
    "REDIS_PORT",
    "QDRANT_HOST",
    "QDRANT_PORT",
    "ERP_BASE_URL",
    "AGENT_URL",
    "AWS_REGION_NAME",
    "AWS_DEFAULT_REGION",
    "MODEL_REASONING",
    "MODEL_GENERATION",
    "MODEL_TRANSLATION",
    "MODEL_EMBEDDING",
    "EMBED_DIM",
    "OCR_LANGS",
    "MONITOR_POLL_SECONDS",
    "RAG_PASS_THRESHOLD",
    "RAG_MAX_RETRIES",
    "CACHE_TTL_SECONDS",
    "LOG_LEVEL",
]


def get_settings() -> dict[str, Any]:
    settings: dict[str, Any] = {}
    missing = []

    for var in REQUIRED_VARS:
        value = os.getenv(var)
        if value in (None, ""):
            missing.append(var)
        else:
            settings[var] = value

    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")

    settings["EMBED_DIM"] = int(settings["EMBED_DIM"])
    settings["POSTGRES_PORT"] = int(settings["POSTGRES_PORT"])
    settings["REDIS_PORT"] = int(settings["REDIS_PORT"])
    settings["QDRANT_PORT"] = int(settings["QDRANT_PORT"])
    settings["MONITOR_POLL_SECONDS"] = int(settings["MONITOR_POLL_SECONDS"])
    settings["RAG_PASS_THRESHOLD"] = float(settings["RAG_PASS_THRESHOLD"])
    settings["RAG_MAX_RETRIES"] = int(settings["RAG_MAX_RETRIES"])
    settings["CACHE_TTL_SECONDS"] = int(settings["CACHE_TTL_SECONDS"])

    return settings


SETTINGS = get_settings()
