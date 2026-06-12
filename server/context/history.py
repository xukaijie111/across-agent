"""历史消息裁剪：调 LLM 前的 working view，不写回 checkpoint。"""

from __future__ import annotations

import os

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages

from context.policy import ContextPolicy


def default_max_history_tokens() -> int:
    return int(os.getenv("CONTEXT_MAX_HISTORY_TOKENS", "6000"))


def _history_token_budget(policy: ContextPolicy) -> int:
    budget = policy.max_history_tokens
    if policy.system_prompt:
        budget -= count_tokens_approximately([SystemMessage(content=policy.system_prompt)])
    return max(budget, policy.min_history_tokens)


def trim_history(messages: list[BaseMessage], policy: ContextPolicy) -> list[BaseMessage]:
    if not messages:
        return messages

    budget = _history_token_budget(policy)
    if count_tokens_approximately(messages) <= budget:
        return messages

    return trim_messages(
        messages,
        max_tokens=budget,
        strategy="last",
        token_counter=count_tokens_approximately,
        start_on="human",
        include_system=False,
        allow_partial=False,
    )
