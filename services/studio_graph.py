"""LangGraph Studio 入口：导出 graph 供 langgraph dev 加载。"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from services.graph.graph import AgentGraphFactory


def make_graph(config: RunnableConfig):
    # checkpointer 由 langgraph.json 里的 generate_checkpointer 注入
    return AgentGraphFactory().build(checkpointer=None)
