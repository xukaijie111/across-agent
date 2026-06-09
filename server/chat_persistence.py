from __future__ import annotations

from typing import Any, AsyncIterator

from events import StreamEvent
from sessions import session_store


async def persist_stream(
    session_id: str,
    user_message: str | None,
    event_iter: AsyncIterator[StreamEvent],
    *,
    title_from_message: str | None = None,
    save_user_message: bool = True,
) -> AsyncIterator[StreamEvent]:
    if save_user_message and user_message:
        session_store.add_message(session_id, "user", user_message)
    if title_from_message:
        session_store.touch_title(session_id, title_from_message)

    chunks: list[str] = []
    final_content = ""
    interrupt_payload: dict[str, Any] | None = None

    async for event in event_iter:
        if event.kind == "delta" and event.content:
            chunks.append(event.content)
        elif event.kind == "done":
            final_content = event.content
        elif event.kind == "interrupt":
            interrupt_payload = event.interrupt
        yield event

    if interrupt_payload is not None:
        session_store.add_message(
            session_id,
            "assistant",
            str(interrupt_payload.get("prompt") or "请确认是否继续"),
            meta={"interrupt": interrupt_payload, "awaiting_action": True},
        )
    else:
        content = final_content or "".join(chunks)
        if content:
            session_store.add_message(session_id, "assistant", content)
