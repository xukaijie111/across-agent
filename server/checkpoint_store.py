"""LangGraph checkpointer（MySQL）。"""

from __future__ import annotations

from checkpoint_mysql import MysqlSaver

_checkpointer: MysqlSaver | None = None


def get_checkpointer() -> MysqlSaver:
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MysqlSaver()
    return _checkpointer
