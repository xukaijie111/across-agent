from __future__ import annotations

from typing import Literal
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, START, END

from services.graph.nodes import AgentNodeRunner
from services.graph.state import AgentState


Route = Literal["tools", "__end__"]


@dataclass
class AgentGraphFactory:
    nodes: AgentNodeRunner = field(default_factory=AgentNodeRunner)

    def route_after_agent(self, state: AgentState) -> Route:
        last = state["messages"][-1]
        if last.get("tool_calls"):
            return "tools"
        return "__end__"

    def build(self):

        builder = StateGraph(AgentState)
        builder.add_node("agent", self.nodes.call_model)
        builder.add_node("tools", self.nodes.execute_tools)
        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent",
            self.route_after_agent,
            {
                "tools": "tools",
                "__end__": END,
            },
        )
        builder.add_edge("tools", "agent")
        return builder.compile()
