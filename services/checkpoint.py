from __future__ import annotations

import sqlite3
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver

from services.config import config

_checkpointer: SqliteSaver | None = None


def get_checkpointer() -> SqliteSaver:
    """单例 checkpointer，与 Session 共用 crossagent.db（不同表）。"""
    global _checkpointer
    if _checkpointer is None:
        db_path = config.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
        _checkpointer.setup()
    return _checkpointer


def thread_config(session_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": session_id}}
