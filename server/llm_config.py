"""从 .env 读取对话 / Embedding 模型，兼容 OPENAI_BASE_URL 别名。"""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

DEFAULT_CHAT_MODEL = "qwen-plus"
DEFAULT_EMBEDDING_MODEL = "text-embedding-v3"


def _ensure_openai_env() -> None:
    if not os.getenv("OPENAI_API_BASE") and os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_API_BASE"] = os.environ["OPENAI_BASE_URL"]


def chat_model_name() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_CHAT_MODEL)


def embedding_model_name() -> str:
    return os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def make_chat_llm(*, temperature: float = 0.7, streaming: bool = False) -> ChatOpenAI:
    _ensure_openai_env()
    return ChatOpenAI(model=chat_model_name(), temperature=temperature, streaming=streaming)


def make_embeddings() -> OpenAIEmbeddings:
    _ensure_openai_env()
    # 百炼等 OpenAI 兼容端点只接受原始字符串，不能先 tokenize
    return OpenAIEmbeddings(
        model=embedding_model_name(),
        check_embedding_ctx_length=False,
        chunk_size=10,  # 百炼 embedding 单次 batch 上限 10
    )
