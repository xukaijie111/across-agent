from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from events import StreamEvent
from registry import AgentInfo, AgentRunner
from subagents.persona import new_state, run_turn


async def _stream_text(text: str) -> AsyncIterator[StreamEvent]:
    for ch in text:
        yield StreamEvent(kind="delta", content=ch)
        await asyncio.sleep(0)
    yield StreamEvent(kind="done", content=text)


class PersonaRunner:
    info = AgentInfo(
        id="persona",
        name="我的分身",
        description="徐先生的数字分身：履历、项目与 Agent/LangChain 经验，RAG 有据回答",
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
        yield StreamEvent(kind="error", message="我的分身不支持确认恢复")
