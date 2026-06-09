from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from events import StreamEvent
from registry import AgentInfo, AgentRunner
from subagents.customer_support import new_state, resume_turn, run_turn


async def _stream_text(text: str) -> AsyncIterator[StreamEvent]:
    for ch in text:
        yield StreamEvent(kind="delta", content=ch)
        await asyncio.sleep(0)
    yield StreamEvent(kind="done", content=text)


class CustomerSupportRunner:
    info = AgentInfo(
        id="customer-support",
        name="服装客服",
        description="衣汇商城 RAG 客服，退货退款支持确认中断",
        enabled=True,
    )

    def create_state(self) -> dict[str, Any]:
        return new_state()

    async def stream_turn(self, state: dict[str, Any], message: str, thread_id: str) -> AsyncIterator[StreamEvent]:
        _ = thread_id
        graph_thread = state.get("thread_id") or thread_id
        if state.get("awaiting_resume"):
            yield StreamEvent(kind="error", message="当前有待确认操作，请先点击继续或取消")
            return

        result = await asyncio.to_thread(run_turn, graph_thread, message)
        if result["status"] == "interrupt":
            state["awaiting_resume"] = True
            state["interrupt"] = result["interrupt"]
            yield StreamEvent(kind="interrupt", interrupt=result["interrupt"])
            return

        state["awaiting_resume"] = False
        state["interrupt"] = None
        async for event in _stream_text(result["response"]):
            yield event

    async def stream_resume(
        self, state: dict[str, Any], decision: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        _ = thread_id
        graph_thread = state.get("thread_id") or thread_id
        if not state.get("awaiting_resume"):
            yield StreamEvent(kind="error", message="当前没有待确认操作")
            return

        result = await asyncio.to_thread(resume_turn, graph_thread, decision)
        state["awaiting_resume"] = False
        state["interrupt"] = None

        if result["status"] == "interrupt":
            state["awaiting_resume"] = True
            state["interrupt"] = result["interrupt"]
            yield StreamEvent(kind="interrupt", interrupt=result["interrupt"])
            return

        async for event in _stream_text(result["response"]):
            yield event
