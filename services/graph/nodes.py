from __future__ import annotations

import json
from typing import Any

from dataclasses import dataclass


from services.context import analyze_messages, format_analysis, trim_messages

from services.graph.state import AgentState

from services.llm import MODEL, client

from services.tools import get_tools, execute_tool


@dataclass
class AgentNodeRunner:

    def call_model(self, state: AgentState) -> dict[str, Any]:

        messages = trim_messages(state["messages"])

        verbose = state.get("verbose", False)

        if verbose:
            print("[context]\n" + format_analysis(analyze_messages(messages)))

        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=get_tools(),
            tool_choice="auto",
        )

        msg = resp.choices[0].message

        return {"messages": [self._to_assistant_message(msg)]}

    def _to_assistant_message(self, msg: dict[str, Any]) -> dict[str, Any]:

        data = {
            "role": "assistant",
            "content": msg.content or "",
        }

        if msg.tool_calls:
            data["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in msg.tool_calls
            ]
        return data

    def execute_tools(self, state: AgentState) -> dict[str, Any]:
        last = state["messages"][-1]

        tool_messages = []

        for tool_call in last.get("tool_calls", []):
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            result = execute_tool(tool_name, tool_args)
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                }
            )
        return {"messages": tool_messages}
