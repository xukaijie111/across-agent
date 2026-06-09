from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol

from events import StreamEvent


@dataclass(frozen=True)
class AgentInfo:
    id: str
    name: str
    description: str
    enabled: bool = True


class AgentRunner(Protocol):
    info: AgentInfo

    def create_state(self) -> dict[str, Any]:
        ...

    async def stream_turn(self, state: dict[str, Any], message: str, thread_id: str) -> AsyncIterator[StreamEvent]:
        ...

    async def stream_resume(
        self, state: dict[str, Any], decision: str, thread_id: str
    ) -> AsyncIterator[StreamEvent]:
        ...


_REGISTRY: dict[str, AgentRunner] = {}


def register(runner: AgentRunner) -> None:
    _REGISTRY[runner.info.id] = runner


def get_runner(agent_id: str) -> AgentRunner:
    runner = _REGISTRY.get(agent_id)
    if runner is None:
        raise KeyError(agent_id)
    if not runner.info.enabled:
        raise ValueError(f"Agent '{agent_id}' is not enabled")
    return runner


def list_agents() -> list[AgentInfo]:
    return [runner.info for runner in _REGISTRY.values()]


def load_runners() -> None:
    from runners.customer_support import CustomerSupportRunner
    from runners.echo import EchoRunner

    register(CustomerSupportRunner())
    register(EchoRunner())
