from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from events import StreamEvent
from registry import AgentInfo, AgentRunner
from subagents.pdf_qa import new_state, run_turn


async def _stream_text(text: str) -> AsyncIterator[StreamEvent]:
    for ch in text:
        yield StreamEvent(kind="delta", content=ch)
        await asyncio.sleep(0)
    yield StreamEvent(kind="done", content=text)


class PdfQaRunner:
    info = AgentInfo(
        id="pdf-qa",
        name="文档问答",
        description="基于内置示例文档的多轮 RAG 问答，仅回答文档中有依据的内容",
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
        yield StreamEvent(kind="error", message="文档问答不支持确认恢复")
