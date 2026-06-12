"""上下文治理插件基类；后续实现 tool 裁剪、重复读清理等。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.messages import BaseMessage

from context.policy import ContextPolicy


class BaseContextPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def process(self, messages: list[BaseMessage], policy: ContextPolicy) -> list[BaseMessage]:
        ...
