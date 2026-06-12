"""从 .env 读取对话 / Embedding 模型；make_chat_llm 默认挂载统一上下文裁剪。"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from context.bridge import govern_prompt_messages

DEFAULT_CHAT_MODEL = "qwen-plus"
DEFAULT_EMBEDDING_MODEL = "text-embedding-v3"


def _ensure_openai_env() -> None:
    if not os.getenv("OPENAI_API_BASE") and os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_API_BASE"] = os.environ["OPENAI_BASE_URL"]


def chat_model_name() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_CHAT_MODEL)


def embedding_model_name() -> str:
    return os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def _govern_messages_input(input: Any) -> Any:
    if isinstance(input, list) and input and isinstance(input[0], BaseMessage):
        return govern_prompt_messages(input)
    return input


def make_chat_llm(*, temperature: float = 0.7, streaming: bool = False, govern: bool = True) -> Runnable:
    _ensure_openai_env()
    llm = ChatOpenAI(model=chat_model_name(), temperature=temperature, streaming=streaming)
    if govern:
        return RunnableLambda(_govern_messages_input) | llm
    return llm


def make_embeddings() -> OpenAIEmbeddings:
    _ensure_openai_env()
    return OpenAIEmbeddings(
        model=embedding_model_name(),
        check_embedding_ctx_length=False,
        chunk_size=10,
    )
