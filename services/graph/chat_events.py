from __future__ import annotations

from typing import Literal, Any, TypedDict, TypeAlias


class TextEvent(TypedDict):
    type: Literal["text"]
    delta: str


class ToolStartEvent(TypedDict):
    type: Literal["tool_start"]
    id: str
    name: str
    args: dict[str, Any]


class ToolEndEvent(TypedDict):
    type: Literal["tool_end"]
    id: str
    result: str | None
    error: str | None


class DoneEvent(TypedDict):
    type: Literal["done"]


class ErrorEvent(TypedDict):
    type: Literal["error"]
    message: str


ChatEvent: TypeAlias = (
    TextEvent | ToolStartEvent | ToolEndEvent | DoneEvent | ErrorEvent
)


MessageRole = Literal["user", "assistant"]


class ClientChatMessage(TypedDict, total=False):
    role: MessageRole
    content: str


class ChatStreamReuqestBody(TypedDict):
    session_id: str
    messages: list[ClientChatMessage]


def text_event(delta: str) -> TextEvent:
    return {"type": "text", "delta": delta}


def tool_start_event(id: str, name: str, args: dict[str, Any]) -> ToolStartEvent:
    return {"type": "tool_start", "id": id, "name": name, "args": args}


def tool_end_event(id: str, result: str | None, error: str | None) -> ToolEndEvent:
    return {"type": "tool_end", "id": id, "result": result, "error": error}


def done_event() -> DoneEvent:
    return {"type": "done"}


def error_event(message: str) -> ErrorEvent:
    return {"type": "error", "message": message}


def is_chat_event(event: Any) -> bool:
    return isinstance(
        event, (TextEvent, ToolStartEvent, ToolEndEvent, DoneEvent, ErrorEvent)
    )
