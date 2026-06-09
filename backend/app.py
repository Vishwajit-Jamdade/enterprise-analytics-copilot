from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai.errors import ClientError
from google.genai import types
from pydantic import BaseModel, Field

from my_agent.agent import root_agent
from my_agent.runtime_config import get_api_key
from my_agent.runtime_config import get_vertex_location
from my_agent.runtime_config import get_vertex_project
from my_agent.runtime_config import load_agent_env
from my_agent.runtime_config import use_vertex_ai

from fastapi.responses import StreamingResponse
import json

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_agent_env()

BASE_DIR = Path(__file__).resolve().parent.parent
CHARTS_DIR = BASE_DIR / "charts"
ADK_DIR = BASE_DIR / ".adk"
SESSION_DB_PATH = ADK_DIR / "chat_sessions.db"
APP_NAME = root_agent.name or "enterprise_data_assistant"
DEFAULT_USER_ID = "demo-user"

TABLE_PATTERN = re.compile(r"\bgold\.[A-Za-z_][A-Za-z0-9_]*\b")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

CHARTS_DIR.mkdir(parents=True, exist_ok=True)
ADK_DIR.mkdir(parents=True, exist_ok=True)

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=SqliteSessionService(db_path=str(SESSION_DB_PATH)),
    auto_create_session=True,
)

app = FastAPI(title="Enterprise Analytics Assistant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/charts", StaticFiles(directory=str(CHARTS_DIR)), name="charts")


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "Enterprise Analytics Assistant API",
        "health": "/api/health",
        "chat": "/api/chat",
        "charts": "/charts",
    }

# @app.post("/api/chat/stream")
# async def chat_stream(payload: ChatRequest):

#     session_id = payload.session_id or uuid4().hex
#     user_id = payload.user_id or DEFAULT_USER_ID

#     async def generate():

#         async for event in runner.run_async(
#             user_id=user_id,
#             session_id=session_id,
#             new_message=_content_from_message(payload.message),
#         ):

#             text = _extract_text(event)

#             if text:

#                 yield (
#                     json.dumps(
#                         {
#                             "type": "message",
#                             "content": text
#                         }
#                     )
#                     + "\n"
#                 )

#     return StreamingResponse(
#         generate(),
#         media_type="text/event-stream"
#     )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    user_id: str | None = None


class ArtifactInfo(BaseModel):
    name: str
    url: str
    kind: Literal["image"] = "image"


class EventSummary(BaseModel):
    id: str
    author: str
    timestamp: float
    text: str = ""
    function_calls: list[dict[str, Any]] = Field(default_factory=list)
    function_responses: list[dict[str, Any]] = Field(default_factory=list)
    artifact_delta: dict[str, int] = Field(default_factory=dict)
    state_delta: dict[str, Any] = Field(default_factory=dict)


class DashboardState(BaseModel):
    session_id: str
    turn_count: int
    tool_count: int
    tool_names: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    artifact: ArtifactInfo | None = None
    summary: str = ""
    last_updated: str = ""


class ChatResponse(BaseModel):
    status: Literal["ok", "error"]
    session_id: str
    user_id: str
    assistant_message: str
    dashboard: DashboardState
    events: list[EventSummary] = Field(default_factory=list)
    artifacts: list[ArtifactInfo] = Field(default_factory=list)
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    auth_mode: str
    api_key_state: str
    databricks_host: str
    session_db: str
    charts_dir: str
    vertex_project: str | None = None
    vertex_location: str | None = None


def _content_from_message(message: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=message)])


def _extract_text(event: Any) -> str:
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return ""

    lines: list[str] = []
    for part in content.parts:
        text = getattr(part, "text", None)
        if text:
            lines.append(text)

    return "\n".join(lines).strip()


def _safe_event_dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_none=True)
    return dict(obj) if isinstance(obj, dict) else {}


def _extract_tables(value: Any) -> list[str]:
    tables: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            tables.update(_extract_tables(item))
    elif isinstance(value, list):
        for item in value:
            tables.update(_extract_tables(item))
    elif value is not None:
        for match in TABLE_PATTERN.findall(str(value)):
            tables.add(match)
    return sorted(tables)


def _chart_url_for_path(path_text: str) -> ArtifactInfo | None:
    candidate = Path(path_text.strip().replace("\\", "/"))
    if candidate.is_absolute():
        return None

    if candidate.suffix.lower() not in IMAGE_SUFFIXES:
        return None

    if len(candidate.parts) == 1:
        resolved = CHARTS_DIR / candidate.name
    elif candidate.parts[0] == "charts":
        resolved = BASE_DIR / candidate
    else:
        resolved = CHARTS_DIR / candidate.name

    try:
        resolved = resolved.resolve()
    except OSError:
        return None

    if not resolved.exists() or not resolved.is_file():
        return None

    if not resolved.is_relative_to(CHARTS_DIR.resolve()):
        return None

    return ArtifactInfo(
        name=resolved.name,
        url=f"/charts/{resolved.name}",
    )


def _discover_artifacts(event: Any, text: str) -> list[ArtifactInfo]:
    found: dict[str, ArtifactInfo] = {}

    artifact_delta = getattr(getattr(event, "actions", None), "artifact_delta", {}) or {}
    for name in artifact_delta:
        artifact = _chart_url_for_path(name)
        if artifact:
            found[artifact.url] = artifact

    for token in re.findall(r"[\w./\\-]+\.(?:png|jpg|jpeg|gif|webp|bmp)", text, flags=re.IGNORECASE):
        artifact = _chart_url_for_path(token)
        if artifact:
            found[artifact.url] = artifact

    return list(found.values())


def _summarize_event(event: Any) -> EventSummary:
    function_calls = [_safe_event_dump(call) for call in (getattr(event, "get_function_calls", lambda: [])())]
    function_responses = [_safe_event_dump(resp) for resp in (getattr(event, "get_function_responses", lambda: [])())]
    text = _extract_text(event)
    actions = getattr(event, "actions", None)

    return EventSummary(
        id=str(getattr(event, "id", "")),
        author=str(getattr(event, "author", "")),
        timestamp=float(getattr(event, "timestamp", 0.0)),
        text=text,
        function_calls=function_calls,
        function_responses=function_responses,
        artifact_delta=dict(getattr(actions, "artifact_delta", {}) or {}),
        state_delta=dict(getattr(actions, "state_delta", {}) or {}),
    )


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _is_gemini_auth_error(error_text: str) -> bool:
    return any(
        token in error_text
        for token in (
            "UNAUTHENTICATED",
            "ACCESS_TOKEN_TYPE_UNSUPPORTED",
            "401",
        )
    )


def _build_dashboard(
    *,
    session_id: str,
    events: list[EventSummary],
    assistant_message: str,
    artifacts: list[ArtifactInfo],
    turn_count: int,
) -> DashboardState:
    tool_names: list[str] = []
    tables: set[str] = set()
    tool_count = 0

    for event in events:
        for call in event.function_calls:
            tool_count += 1
            tool_name = str(call.get("name", "")).strip()
            if tool_name:
                tool_names.append(tool_name)

            tables.update(_extract_tables(call.get("args")))

        for response in event.function_responses:
            tables.update(_extract_tables(response.get("response")))
            tables.update(_extract_tables(response.get("name")))

        tables.update(_extract_tables(event.text))

    tool_names = list(dict.fromkeys(tool_names))
    primary_artifact = artifacts[0] if artifacts else None

    return DashboardState(
        session_id=session_id,
        turn_count=turn_count,
        tool_count=tool_count,
        tool_names=tool_names,
        tables=sorted(tables),
        artifact=primary_artifact,
        summary=_first_non_empty_line(assistant_message),
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    auth_mode = "vertex" if use_vertex_ai() else "gemini_api"
    api_key_state = "configured" if get_api_key() else "missing"
    return HealthResponse(
        status="ok",
        auth_mode=auth_mode,
        api_key_state=api_key_state,
        databricks_host="configured" if os.getenv("DATABRICKS_HOST") else "missing",
        session_db=str(SESSION_DB_PATH),
        charts_dir=str(CHARTS_DIR),
        vertex_project=get_vertex_project(),
        vertex_location=get_vertex_location() if use_vertex_ai() else None,
    )


@app.get("/api/charts/{filename:path}")
async def chart_file(filename: str) -> FileResponse:
    file_path = (CHARTS_DIR / filename).resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Chart not found")
    if not file_path.is_relative_to(CHARTS_DIR.resolve()):
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(file_path)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    session_id = payload.session_id or uuid4().hex
    user_id = payload.user_id or DEFAULT_USER_ID

    events: list[EventSummary] = []
    artifacts: dict[str, ArtifactInfo] = {}
    assistant_parts: list[str] = []

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=_content_from_message(payload.message),
        ):
            summary = _summarize_event(event)
            events.append(summary)

            if summary.author != "user" and summary.text:
                if not summary.function_calls and not summary.function_responses:
                    assistant_parts.append(summary.text)

            for artifact in _discover_artifacts(event, summary.text):
                artifacts[artifact.url] = artifact

        session = await runner.session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        turn_count = len(session.events) if session else len(events)
        assistant_message = "\n\n".join(assistant_parts).strip()
        if not assistant_message:
            assistant_message = "The agent completed the request."
        artifact_list = list(artifacts.values())
        dashboard = _build_dashboard(
            session_id=session_id,
            events=events,
            assistant_message=assistant_message,
            artifacts=artifact_list,
            turn_count=turn_count,
        )
        if artifact_list and not dashboard.artifact:
            dashboard.artifact = artifact_list[0]

        return ChatResponse(
            status="ok",
            session_id=session_id,
            user_id=user_id,
            assistant_message=assistant_message,
            dashboard=dashboard,
            events=events,
            artifacts=artifact_list,
        )
    except ClientError as exc:  # pragma: no cover - surfaced to the UI
        logger.exception("Agent run failed")
        error_text = str(exc)
        if _is_gemini_auth_error(error_text):
            error_message = (
                "Gemini authentication failed. If you are using a Gemini API"
                " key, put it in GEMINI_API_KEY or GOOGLE_API_KEY in the root"
                " .env. If you are using a Vertex AI or Google Cloud API key,"
                " set GOOGLE_GENAI_USE_VERTEXAI=true (and project/location if"
                " required), then restart the backend."
            )
        else:
            error_message = f"Agent run failed: {exc}"

        dashboard = _build_dashboard(
            session_id=session_id,
            events=events,
            assistant_message=error_message,
            artifacts=list(artifacts.values()),
            turn_count=len(events),
        )
        return ChatResponse(
            status="error",
            session_id=session_id,
            user_id=user_id,
            assistant_message=error_message,
            dashboard=dashboard,
            events=events,
            artifacts=list(artifacts.values()),
            error=str(exc),
        )
    except Exception as exc:  # pragma: no cover - surfaced to the UI
        logger.exception("Agent run failed")
        error_text = str(exc)
        if _is_gemini_auth_error(error_text):
            error_message = (
                "Gemini authentication failed. If you are using a Gemini API"
                " key, put it in GEMINI_API_KEY or GOOGLE_API_KEY in the root"
                " .env. If you are using a Vertex AI or Google Cloud API key,"
                " set GOOGLE_GENAI_USE_VERTEXAI=true (and project/location if"
                " required), then restart the backend."
            )
        else:
            error_message = f"Agent run failed: {exc}"
        dashboard = _build_dashboard(
            session_id=session_id,
            events=events,
            assistant_message=error_message,
            artifacts=list(artifacts.values()),
            turn_count=len(events),
        )
        return ChatResponse(
            status="error",
            session_id=session_id,
            user_id=user_id,
            assistant_message=error_message,
            dashboard=dashboard,
            events=events,
            artifacts=list(artifacts.values()),
            error=str(exc),
        )
@app.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest):

    session_id = payload.session_id or uuid4().hex
    user_id = payload.user_id or DEFAULT_USER_ID

    async def generate():

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=_content_from_message(payload.message),
        ):

            text = _extract_text(event)

            if text:

                yield (
                    json.dumps(
                        {
                            "type": "message",
                            "content": text,
                        }
                    )
                    + "\n"
                )

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("backend.app:app", host="0.0.0.0", port=8001, reload=True)
