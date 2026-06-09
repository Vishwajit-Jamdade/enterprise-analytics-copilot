from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            if load_dotenv(path, override=False, encoding=encoding):
                return
        except UnicodeDecodeError:
            continue


@lru_cache(maxsize=1)
def load_agent_env() -> None:
    _load_env_file(ROOT_DIR / ".env")


def get_api_key() -> str | None:
    load_agent_env()
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def use_vertex_ai() -> bool:
    load_agent_env()
    value = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    return bool(
        os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_LOCATION")
    )


def get_vertex_project() -> str | None:
    load_agent_env()
    return os.getenv("GOOGLE_CLOUD_PROJECT")


def get_vertex_location() -> str:
    load_agent_env()
    return os.getenv("GOOGLE_CLOUD_LOCATION", "global")
