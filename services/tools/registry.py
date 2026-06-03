from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool, tool
from langchain_core.utils.function_calling import convert_to_openai_tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, t: BaseTool) -> BaseTool:
        if t.name in self._tools:
            raise ValueError(f"Tool {t.name!r} already registered")
        self._tools[t.name] = t
        return t

    def register_many(
        self,
        tools: list[BaseTool],
        *,
        skip_existing: bool = True,
    ) -> list[str]:
        registered: list[str] = []
        for t in tools:
            if skip_existing and t.name in self._tools:
                continue
            if t.name in self._tools:
                raise ValueError(f"Tool {t.name!r} already registered")
            self._tools[t.name] = t
            registered.append(t.name)
        return registered

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def openai_tools(self) -> list[dict[str, Any]]:
        return [convert_to_openai_tool(t) for t in self._tools.values()]

    def invoke(self, name: str, args: dict[str, Any]) -> str:
        t = self._tools.get(name)
        if t is None:
            return f'{{"ok": false, "error": "unknown tool: {name}"}}'
        try:
            result = t.invoke(args)
        except Exception as exc:
            return f'{{"ok": false, "error": {exc!r}}}'
        return result if isinstance(result, str) else str(result)


registry = ToolRegistry()


def register_tool(
    *,
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable[..., str]], BaseTool]:
    def decorator(fn: Callable[..., str]) -> BaseTool:
   
        t = tool()(fn) 
        return registry.register(t)

    return decorator
