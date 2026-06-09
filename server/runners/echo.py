from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from events import StreamEvent
from registry import AgentInfo, AgentRunner
from subagents.chat_assistant import new_state, run_turn


async def _stream_text(text: str) -> AsyncIterator[StreamEvent]:
    for ch in text:
        yield StreamEvent(kind="delta", content=ch)
        await asyncio.sleep(0)
    yield StreamEvent(kind="done", content=text)


class EchoRunner:
    """日常聊天助手（id 保留 echo 以兼容前端）。"""

    info = AgentInfo(
        id="echo",
        name="聊天助手",
        description="日常闲聊，不联网，不确定不编造",
        enabled=True,
    )

    def create_state(self) -> dict[str, Any]:
        return new_state()

    async def stream_turn(self, state: dict[str, Any], message: str, thread_id: str) -> AsyncIterator[StreamEvent]:
        _ = thread_id
        text = await asyncio.to_thread(run_turn, state, message)
        async for event in _stream_text(text):
            yield event

    async def stream_resume(
        self, state: dict[str, Any], decision: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        _ = (state, decision, thread_id)
        yield StreamEvent(kind="error", message="聊天助手不支持确认恢复")
