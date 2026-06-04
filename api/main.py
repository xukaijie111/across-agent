from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.graph.chat_events import ChatEvent, error_event
from services.graph.stream_runner import default_stream_runner
from typing import Generator

app = FastAPI(title="CrossAgent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClientMessage(BaseModel):
    role: str
    content: str = ""


class ChatStreamRequestBody(BaseModel):
    session_id: str
    messages: list[ClientMessage] = Field(default_factory=list)


def _sse_frame(event: ChatEvent, event_id: int) -> str:

    return "\n".join(
        [
            f"id:evt-{event_id}",
            f"event:chat",
            f"data:{json.dumps(event,ensure_ascii=False)}",
            "",
            "",
        ]
    )


@app.post("/chat/stream")
async def chat_stream(body: ChatStreamRequestBody) -> StreamingResponse:

    if not body.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    client_messages = [m.model_dump() for m in body.messages]

    event_id = 0

    def event_generator() -> Generator[str, None]:

        try:
            nonlocal event_id

            for event in default_stream_runner.stream_turn(client_messages):
                event_id += 1
                yield _sse_frame(event, event_id)
        except Exception as exc:
            seq += 1
            yield _sse_frame(error_event(f"agent failed: {exc}"), seq)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    )
