"""
日常聊天助手：LangGraph 编排；上下文裁剪由 make_chat_llm 统一注入，不写回 checkpoint。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from llm_config import make_chat_llm

PROJECT_ROOT = SERVER_ROOT.parent
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

_compiled_graph = None


class ChatState(TypedDict):
    messages: list[BaseMessage]
    response: str


def _dict_history_to_messages(history: list[dict[str, str]]) -> list[BaseMessage]:
    items: list[BaseMessage] = []
    for msg in history:
        if msg["role"] == "user":
            items.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            items.append(AIMessage(content=msg["content"]))
    return items


def chat_node(state: ChatState) -> ChatState:
    prompt = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    llm = make_chat_llm(temperature=0.7)
    response = llm.invoke(prompt)
    text = response.content if isinstance(response.content, str) else str(response.content)
    text = text.strip() or "抱歉，我这次没有想好怎么回答。"
    return {
        "messages": [*state["messages"], AIMessage(content=text)],
        "response": text,
    }


def build_graph() -> StateGraph:
    graph = StateGraph(ChatState)
    graph.add_node("chat", chat_node)
    graph.set_entry_point("chat")
    graph.add_edge("chat", END)
    return graph


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph


def new_state() -> dict[str, Any]:
    return {"messages": [], "awaiting_resume": False, "interrupt": None}


def run_turn(state: dict[str, Any], message: str) -> str:
    history = _dict_history_to_messages(state.get("messages", []))
    payload: ChatState = {
        "messages": [*history, HumanMessage(content=message)],
        "response": "",
    }
    result = get_compiled_graph().invoke(payload)
    text = result["response"]

    state["messages"] = [
        *state.get("messages", []),
        {"role": "user", "content": message},
        {"role": "assistant", "content": text},
    ]
    return text


def main() -> None:
    state = new_state()
    print("日常聊天助手（LangGraph），输入 quit 退出。\n")
    while True:
        user_input = input("你: ").strip()
        if user_input.lower() in ("quit", "exit", "q") or user_input in ("退出", "再见"):
            break
        if not user_input:
            continue
        print(f"\n助手: {run_turn(state, user_input)}\n")


if __name__ == "__main__":
    main()
