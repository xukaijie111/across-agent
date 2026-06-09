from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class StreamEvent:
    kind: Literal["delta", "interrupt", "done", "error"]
    content: str = ""
    interrupt: dict[str, Any] | None = None
    message: str = ""
