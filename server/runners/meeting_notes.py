from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from events import StreamEvent
from registry import AgentInfo, AgentRunner
from subagents.meeting_notes import new_state, run_turn


async def _stream_text(text: str) -> AsyncIterator[StreamEvent]:
    for ch in text:
        yield StreamEvent(kind="delta", content=ch)
        await asyncio.sleep(0)
    yield StreamEvent(kind="done", content=text)


class MeetingNotesRunner:
    info = AgentInfo(
        id="meeting-notes",
        name="会议纪要",
        description="粘贴会议文字稿，生成结构化纪要（摘要/决策/待办）",
        enabled=True,
    )

    def create_state(self) -> dict[str, Any]:
        return new_state()

    async def stream_turn(self, state: dict[str, Any], message: str, thread_id: str) -> AsyncIterator[StreamEvent]:
        _ = state
        result = await asyncio.to_thread(run_turn, thread_id, message)
        if result.get("status") != "complete":
            yield StreamEvent(kind="error", message="纪要生成未完成")
            return
        async for event in _stream_text(result.get("response", "")):
            yield event

    async def stream_resume(
        self, state: dict[str, Any], decision: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        _ = (state, decision, thread_id)
        yield StreamEvent(kind="error", message="会议纪要不支持确认恢复")
