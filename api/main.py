from __future__ import annotations

import json
from typing import Generator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.graph.chat_events import ChatEvent, error_event
from services.graph.stream_runner import default_stream_runner
from services.session import session_service

app = FastAPI(title="CrossAgent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatStreamRequestBody(BaseModel):
    session_id: str
    message: str = Field(min_length=1)


def _sse_frame(event: ChatEvent, event_id: int) -> str:
    return "\n".join(
        [
            f"id: evt-{event_id}",
            "event: chat",
            f"data: {json.dumps(event, ensure_ascii=False)}",
            "",
            "",
        ]
    )


@app.post("/chat/stream")
def chat_stream(body: ChatStreamRequestBody) -> StreamingResponse:
    if not session_service.get_session(body.session_id):
        raise HTTPException(status_code=404, detail="session not found")
    user_input = body.message.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="message is empty")

    event_id = 0

    def event_generator() -> Generator[str, None, None]:
        nonlocal event_id
        try:
            for event in default_stream_runner.stream_turn(body.session_id, user_input):
                event_id += 1
                yield _sse_frame(event, event_id)
        except Exception as exc:
            event_id += 1
            yield _sse_frame(error_event(f"agent failed: {exc}"), event_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )


@app.post("/session/create")
def create_session() -> dict[str, str]:
    session_id = session_service.create()
    return {"session_id": session_id}


@app.post("/session/histroy")
def get_session_history(session_id: str) -> list[dict]:
    if not session_service.get_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    return default_stream_runner.get_ui_messages(session_id)
