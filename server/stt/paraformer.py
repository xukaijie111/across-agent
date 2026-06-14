"""DashScope Paraformer：本地 wav 文件非流式识别。"""

from __future__ import annotations

import os
from typing import Any

import dashscope
from dashscope.audio.asr import Recognition
from http import HTTPStatus


def _ensure_dashscope_api_key() -> None:
    if os.getenv("DASHSCOPE_API_KEY"):
        return
    key = os.getenv("OPENAI_API_KEY") or os.getenv("UPSTREAM_API_KEY")
    if key:
        dashscope.api_key = key


def _extract_text(sentence: Any) -> str:
    if sentence is None:
        return ""
    if isinstance(sentence, dict):
        return str(sentence.get("text") or "").strip()
    if isinstance(sentence, list):
        parts = [_extract_text(item) for item in sentence]
        return "".join(parts).strip()
    return str(sentence).strip()


def transcribe_wav_file(path: str, *, language_hints: list[str] | None = None) -> str:
    _ensure_dashscope_api_key()
    if not dashscope.api_key and not os.getenv("DASHSCOPE_API_KEY"):
        raise RuntimeError("未配置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY")

    recognition = Recognition(
        model="paraformer-realtime-v2",
        format="wav",
        sample_rate=16000,
        language_hints=language_hints or ["zh", "en"],
        callback=None,
    )
    result = recognition.call(path)
    if result.status_code != HTTPStatus.OK:
        message = getattr(result, "message", None) or "语音识别失败"
        raise RuntimeError(message)

    text = _extract_text(result.get_sentence())
    if not text:
        raise RuntimeError("未识别到有效语音内容")
    return text
