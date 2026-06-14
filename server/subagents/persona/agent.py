"""
个人分身 Agent — 基于简历与 Agent 知识库的 RAG 问答。

以第一人称代表徐先生回答履历、项目与技术面问题；仅依据内置知识库，不编造。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

SERVER_ROOT = Path(__file__).resolve().parents[2]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from llm_config import make_chat_llm, make_embeddings

PROJECT_ROOT = SERVER_ROOT.parent
KNOWLEDGE_PATH = Path(__file__).resolve().parent / "knowledge.md"
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(SERVER_ROOT / ".env")

PERSONA_NAME = "徐开洁"

_BUILTIN_DOC_REVISION = "persona-v6"

_vectorstore: FAISS | None = None
_doc_source = "builtin"
_index_revision: str | None = None

SYSTEM_PROMPT = f"""你是「{PERSONA_NAME}」的数字分身，代替本人与访客对话。

要求：
- 根据检索到的个人资料回答，涵盖履历、项目、技能、Agent/LangChain 观点
- 使用第一人称「我」作答（代表{PERSONA_NAME}）
- 使用简体中文，语气专业、诚恳、简洁
- 仅依据资料作答；资料未提及或不确定时，明确说「这个我资料里没写清楚」或「我不太确定」，不要编造
- 支持多轮追问，结合对话上下文理解指代

相关个人资料片段：
{{context}}"""

_HINT_REPLY = (
    f"你好，我是{PERSONA_NAME}的数字分身，可以帮你了解我的履历和 Agent 相关经验。\n\n"
    "你可以问我：\n"
    "· 我的工作经历和代表项目有哪些？\n"
    "· 我在 LangChain / Agent 工程化方面熟悉什么？\n"
    "· 我做过哪些上下文治理、HITL、RAG 相关实践？\n\n"
    "我会只根据内置资料回答，支持多轮追问。"
)

_GREETINGS = frozenset({"你好", "您好", "hi", "hello", "嗨", "在吗"})


def _load_builtin_doc() -> str:
    return KNOWLEDGE_PATH.read_text(encoding="utf-8")


def _needs_hint(message: str) -> bool:
    text = message.strip()
    if not text:
        return True
    lower = text.lower()
    return lower in _GREETINGS or text in _GREETINGS


def _split_documents(text: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    return splitter.split_documents([Document(page_content=text.strip())])


def build_index(doc_text: str) -> FAISS:
    global _vectorstore, _doc_source, _index_revision
    docs = _split_documents(doc_text)
    embeddings = make_embeddings()
    _vectorstore = FAISS.from_documents(docs, embeddings)
    _doc_source = "custom"
    _index_revision = None
    return _vectorstore


def get_vectorstore() -> FAISS:
    global _vectorstore, _doc_source, _index_revision
    stale = _vectorstore is None or (
        _doc_source == "builtin" and _index_revision != _BUILTIN_DOC_REVISION
    )
    if stale:
        docs = _split_documents(_load_builtin_doc())
        embeddings = make_embeddings()
        _vectorstore = FAISS.from_documents(docs, embeddings)
        _index_revision = _BUILTIN_DOC_REVISION
        _doc_source = "builtin"
    return _vectorstore


def _retrieve(query: str, k: int = 5) -> str:
    store = get_vectorstore()
    hits = store.similarity_search(query, k=k)
    if not hits:
        return "（未检索到相关片段）"
    return "\n\n---\n\n".join(d.page_content for d in hits)


def _to_langchain_messages(history: list[dict[str, str]], context: str) -> list:
    items: list = [SystemMessage(content=SYSTEM_PROMPT.format(context=context))]
    for msg in history:
        if msg["role"] == "user":
            items.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            items.append(AIMessage(content=msg["content"]))
    return items


def new_state() -> dict[str, Any]:
    return {"messages": [], "awaiting_resume": False, "interrupt": None}


def run_turn(state: dict[str, Any], message: str) -> str:
    history = state.get("messages", [])
    if _needs_hint(message):
        state["messages"] = [
            *history,
            {"role": "user", "content": message},
            {"role": "assistant", "content": _HINT_REPLY},
        ]
        return _HINT_REPLY

    context = _retrieve(message)
    llm = make_chat_llm(temperature=0.2)
    messages = [
        *_to_langchain_messages(history, context),
        HumanMessage(content=message),
    ]
    response = llm.invoke(messages)
    text = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    text = text.strip() or "抱歉，我暂时无法根据资料回答这个问题。"

    state["messages"] = [
        *history,
        {"role": "user", "content": message},
        {"role": "assistant", "content": text},
    ]
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal persona RAG agent")
    parser.add_argument(
        "--text", help="自定义知识库 Markdown 路径（默认 knowledge.md）"
    )
    parser.add_argument("--question", help="单次提问")
    args = parser.parse_args()

    if args.text:
        doc = Path(args.text).read_text(encoding="utf-8")
        build_index(doc)
        print(f"已索引：{args.text}\n")
    else:
        get_vectorstore()
        print(f"已加载内置知识库：{KNOWLEDGE_PATH.name}\n")

    if args.question:
        print(run_turn(new_state(), args.question))
        return

    print("分身问答就绪，输入 quit 退出。\n")
    state = new_state()
    while True:
        try:
            question = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue
        print(f"\n分身: {run_turn(state, question)}\n")


if __name__ == "__main__":
    main()
