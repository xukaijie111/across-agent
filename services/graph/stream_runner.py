from __future__ import annotations

import json

from typing import Any, Iterable


from services.context import trim_messages
from services.graph.runner import SYSTEM_PROMPT
from services.graph.state import AgentState
from services.graph.graph import AgentGraphFactory

from services.graph.chat_events import (
    ClientChatMessage,
    ChatStreamReuqestBody,
    text_event,
    tool_start_event,
    tool_end_event,
    done_event,
    error_event,
    ChatEvent,
)


def _parse_tool_args(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _tool_payload(content: str) -> tuple[str | None, str | None]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return content, None
    if isinstance(data, dict) and data.get("ok") is False:
        return None, content
    return content, None


def _openai_messages_from_client(
    client_messages: list[ClientChatMessage],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    for msg in client_messages:
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue
        item: dict[str, Any] = {
            "role": role,
            "content": msg.get("content") or "",
        }
        if msg.get("tool_calls"):
            item["tool_calls"] = msg["tool_calls"]
        out.append(item)
    return out


class StreamRunner:
    def __init__(self):
        self._graph = AgentGraphFactory().build()

    def stream_turn(
        self,
        client_messages: list[ClientChatMessage],
        *,
        verbose: bool = False,
    ) -> Iterable[ChatEvent]:

        messages = trim_messages(_openai_messages_from_client(client_messages))

        state = {"messages": messages, "verbose": verbose}

        final_assistant: dict[str, Any] | None = None

        for update in self._graph.stream(state, stream_mode="updates"):

            if "agent" in update:

                msg = update["agent"].get("messages") or []

                if not msg:
                    continue

                last = msg[-1]

                if last.get("tool_calls"):
                    for tc in last["tool_calls"]:

                        fn = tc.get("function") or {}
                        yield tool_start_event(
                            tc.get("id") or "",
                            fn.get("name") or "",
                            _parse_tool_args(fn.get("arguments") or "{}"),
                        )

                else:
                    final_assistant = last

            if "tools" in update:
                for tool_msg in update["tools"].get("messages") or []:
                    content = tool_msg.get("content") or ""
                    result, error = _tool_payload(content)
                    yield tool_end_event(
                        tool_msg.get("tool_call_id") or "",
                        result,
                        error,
                    )
        if final_assistant:
            content = final_assistant.get("content") or ""
            if content:
                yield text_event(content)
        yield done_event()


default_stream_runner = StreamRunner()
