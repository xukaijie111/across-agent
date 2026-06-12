"""上下文治理入口：历史裁剪内置；插件槽位预留给后续扩展。"""

from __future__ import annotations

from typing import Protocol

from langchain_core.messages import BaseMessage

from context.history import trim_history
from context.policy import ContextPolicy


class ContextPlugin(Protocol):
    def process(self, messages: list[BaseMessage], policy: ContextPolicy) -> list[BaseMessage]:
        ...


_PLUGINS: list[ContextPlugin] = []


def register_plugin(plugin: ContextPlugin) -> None:
    _PLUGINS.append(plugin)


def govern_messages(
    messages: list[BaseMessage],
    policy: ContextPolicy | None = None,
) -> list[BaseMessage]:
    """构建发给 LLM 的 working view；原始 messages 保持不变。"""
    effective = policy or ContextPolicy()
    result = trim_history(messages, effective)
    for plugin in _PLUGINS:
        result = plugin.process(result, effective)
    return result
