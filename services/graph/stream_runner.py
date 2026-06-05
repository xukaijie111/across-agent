from __future__ import annotations

import json
from typing import Any, Iterable

from services.checkpoint import thread_config
from services.context import trim_messages
from services.graph.chat_events import (
    ChatEvent,
    done_event,
    text_event,
    tool_end_event,
    tool_start_event,
)
from services.graph.graph import AgentGraphFactory
from services.graph.runner import SYSTEM_PROMPT
from services.graph.state import AgentState


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


def _build_input_messages(
    user_input: str,
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not existing:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]
    return [{"role": "user", "content": user_input}]


class StreamRunner:
    def __init__(self) -> None:
        self._graph = AgentGraphFactory().build()

    def get_ui_messages(self, session_id: str) -> list[dict[str, str]]:
        snapshot = self._graph.get_state(thread_config(session_id))
        raw = snapshot.values.get("messages") or []
        out: list[dict[str, str]] = []
        for msg in raw:
            role = msg.get("role")
            if role == "user":
                out.append(
                    {
                        "role": "user",
                        "content": msg.get("content") or "",
                        "format": "plain",
                    }
                )
            elif role == "assistant" and not msg.get("tool_calls"):
                content = msg.get("content") or ""
                if content:
                    out.append(
                        {
                            "role": "assistant",
                            "content": content,
                            "format": "markdown",
                        }
                    )
        return out

    def stream_turn(
        self,
        session_id: str,
        user_input: str,
        *,
        verbose: bool = False,
    ) -> Iterable[ChatEvent]:
        config = thread_config(session_id)
        snapshot = self._graph.get_state(config)
        existing = snapshot.values.get("messages") or []

        input_messages = trim_messages(_build_input_messages(user_input, existing))
        state: AgentState = {"messages": input_messages, "verbose": verbose}

        final_assistant: dict[str, Any] | None = None

        for update in self._graph.stream(
            state,
            config=config,
            stream_mode="updates",
        ):
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
