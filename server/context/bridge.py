"""调 LLM 前的统一 prompt 治理：拆 system、裁历史、跑插件链。"""

from __future__ import annotations

from langchain_core.messages import BaseMessage, SystemMessage

from context.governor import govern_messages
from context.history import default_max_history_tokens
from context.policy import ContextPolicy


def _system_text(message: SystemMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return str(content)


def govern_prompt_messages(
    messages: list[BaseMessage],
    policy: ContextPolicy | None = None,
) -> list[BaseMessage]:
    """裁剪即将发给模型的 messages；首条 SystemMessage 保留，只裁后续对话。"""
    if not messages:
        return messages

    system_msg: SystemMessage | None = None
    rest = messages
    if isinstance(messages[0], SystemMessage):
        system_msg = messages[0]
        rest = messages[1:]

    system_prompt = _system_text(system_msg) if system_msg else None
    effective = policy or ContextPolicy(
        max_history_tokens=default_max_history_tokens(),
        system_prompt=system_prompt,
    )
    governed = govern_messages(rest, effective)
    if system_msg is not None:
        return [system_msg, *governed]
    return governed
