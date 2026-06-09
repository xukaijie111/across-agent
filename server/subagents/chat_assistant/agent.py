"""
日常聊天助手：普通闲聊，不联网，不确定不编造。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from llm_config import make_chat_llm

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

SYSTEM_PROMPT = """你是一个日常聊天助手，风格轻松友好。

能力边界：
- 只做普通闲聊、简单问答与生活建议
- 不能联网搜索，不能查询实时信息（天气、股价、新闻等）
- 不是专业客服、医生、律师或技术支持，不负责处理订单、退货等业务

回答要求：
- 使用简体中文
- 不确定或超出能力的问题，直接说「我不太确定」或「我没有可靠信息」，不要编造
- 不要假装搜索过或查过资料
- 回复简洁自然，一般不超过 120 字"""


def new_state() -> dict[str, Any]:
    return {"messages": [], "awaiting_resume": False, "interrupt": None}


def _to_langchain_messages(history: list[dict[str, str]]) -> list:
    items = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        if msg["role"] == "user":
            items.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            items.append(AIMessage(content=msg["content"]))
    return items


def run_turn(state: dict[str, Any], message: str) -> str:
    llm = make_chat_llm(temperature=0.7)
    messages = [*_to_langchain_messages(state.get("messages", [])), HumanMessage(content=message)]
    response = llm.invoke(messages)
    text = response.content or "抱歉，我这次没有想好怎么回答。"
    state["messages"] = [
        *state.get("messages", []),
        {"role": "user", "content": message},
        {"role": "assistant", "content": text},
    ]
    return text
