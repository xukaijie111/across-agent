"""LangGraph Studio / langgraph dev 用的 checkpointer，与 FastAPI 共用 crossagent.db。"""
from __future__ import annotations

import contextlib

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from services.config import config


@contextlib.asynccontextmanager
async def generate_checkpointer():
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(config.db_path)) as saver:
        await saver.setup()
        yield saver
