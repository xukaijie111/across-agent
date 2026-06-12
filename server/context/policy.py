from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextPolicy:
    """治理策略；token 估算统一走 LangChain count_tokens_approximately。"""

    max_history_tokens: int = 6000
    min_history_tokens: int = 256
    system_prompt: str | None = None
    max_tool_result_chars: int | None = None
