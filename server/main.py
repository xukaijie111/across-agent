from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

from contextlib import asynccontextmanager

import context.bootstrap  # noqa: E402, F401 — 启动时注册上下文治理插件

from chat_persistence import persist_stream  # noqa: E402
from db import init_mysql  # noqa: E402
from events import StreamEvent  # noqa: E402
from registry import get_runner, list_agents, load_runners  # noqa: E402
from sessions import session_store  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_mysql()
    load_runners()
    yield


app = FastAPI(title="Agent Playground API", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateSessionRequest(BaseModel):
    agent_id: str
    resume_session_id: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    agent_id: str
    resumed: bool = False


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1)


class ResumeRequest(BaseModel):
    session_id: str
    decision: Literal["confirm", "cancel"]


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _emit_event(event: StreamEvent) -> str:
    if event.kind == "delta":
        return _sse("delta", {"content": event.content})
    if event.kind == "interrupt":
        return _sse("interrupt", event.interrupt or {})
    if event.kind == "done":
        return _sse("done", {"content": event.content})
    return _sse("error", {"message": event.message or "unknown error"})


_CHAT_HISTORY_AGENTS = frozenset({"echo", "persona"})


def _restore_echo_messages(session) -> None:
    if session.agent_id not in _CHAT_HISTORY_AGENTS:
        return
    history = []
    for msg in session_store.list_messages(session.session_id):
        if msg.meta and msg.meta.get("awaiting_action"):
            continue
        if msg.role in {"user", "assistant"}:
            history.append({"role": msg.role, "content": msg.content})
    session.state["messages"] = history


def _message_to_client(msg) -> dict[str, Any]:
    payload = {
        "id": msg.message_id,
        "role": msg.role,
        "content": msg.content,
    }
    if msg.meta:
        if msg.meta.get("interrupt"):
            payload["interrupt"] = msg.meta["interrupt"]
        if msg.meta.get("awaiting_action"):
            payload["awaiting_action"] = True
    return payload


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "mysql": True}


@app.get("/api/agents")
def agents() -> list[dict[str, Any]]:
    return [
        {
            "id": info.id,
            "name": info.name,
            "description": info.description,
            "enabled": info.enabled,
        }
        for info in list_agents()
    ]


@app.get("/api/sessions")
def list_sessions(agent_id: str, limit: int = 30) -> list[dict[str, Any]]:
    sessions = session_store.list_by_agent(agent_id, limit=limit)
    return [
        {
            "session_id": s.session_id,
            "agent_id": s.agent_id,
            "title": s.title,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions
    ]


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _restore_echo_messages(session)
    return {
        "session_id": session.session_id,
        "agent_id": session.agent_id,
        "title": session.title,
        "state": {
            "awaiting_resume": session.state.get("awaiting_resume", False),
            "interrupt": session.state.get("interrupt"),
        },
    }


@app.get("/api/sessions/{session_id}/messages")
def get_session_messages(session_id: str) -> list[dict[str, Any]]:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return [_message_to_client(m) for m in session_store.list_messages(session_id)]


@app.post("/api/sessions", response_model=CreateSessionResponse)
def create_session(body: CreateSessionRequest) -> CreateSessionResponse:
    try:
        runner = get_runner(body.agent_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {body.agent_id}") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if body.resume_session_id:
        existing = session_store.get(body.resume_session_id)
        if existing and existing.agent_id == body.agent_id:
            _restore_echo_messages(existing)
            return CreateSessionResponse(
                session_id=existing.session_id,
                agent_id=existing.agent_id,
                resumed=True,
            )

    session = session_store.create(body.agent_id, runner.create_state())
    return CreateSessionResponse(session_id=session.session_id, agent_id=session.agent_id, resumed=False)


@app.post("/api/sessions/{session_id}/reset")
def reset_session(session_id: str) -> dict[str, str]:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    runner = get_runner(session.agent_id)
    updated = session_store.reset(session_id, runner.create_state())
    assert updated is not None
    return {"session_id": session_id, "status": "reset"}


@app.post("/api/chat/stream")
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    session = session_store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        runner = get_runner(session.agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is empty")

    _restore_echo_messages(session)

    async def event_generator():
        yield _sse("meta", {"session_id": session.session_id, "agent_id": session.agent_id})
        try:
            stream = runner.stream_turn(session.state, message, session.session_id)
            async for event in persist_stream(
                session.session_id,
                message,
                stream,
                title_from_message=message[:40],
            ):
                yield _emit_event(event)
            session_store.update_state(session.session_id, session.state)
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/resume")
async def chat_resume(body: ResumeRequest) -> StreamingResponse:
    session = session_store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        runner = get_runner(session.agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_store.clear_awaiting_messages(session.session_id)

    async def event_generator():
        yield _sse("meta", {"session_id": session.session_id, "agent_id": session.agent_id, "resume": body.decision})
        try:
            stream = runner.stream_resume(session.state, body.decision, session.session_id)
            async for event in persist_stream(session.session_id, None, stream, save_user_message=False):
                yield _emit_event(event)
            session_store.update_state(session.session_id, session.state)
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
