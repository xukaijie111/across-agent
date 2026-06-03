

from __future__ import annotations
from typing import Annotated,Any

from operator import add

from typing_extensions import TypedDict

class AgentState(TypedDict):
    messages:Annotated[list[dict[str, Any]], add]
    verbose:bool