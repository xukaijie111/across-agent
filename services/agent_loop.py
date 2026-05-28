import json

from services.context import analyze_messages, format_analysis, trim_messages
from services.llm import MODEL, client
from services.tools import TOOLS, execute_tool

SYSTEM_PROMPT = """你是一个多端小程序开发助手，熟悉 uni-app、Taro、Morjs。
当用户需要检测项目或执行构建时，必须调用对应工具，不要编造结果。
工具返回 JSON 后，用中文简洁总结。"""


def _assemble_messages(message) -> dict:
    data = {
        "role": "assistant",
        "content": message.content or "",
    }
    if message.tool_calls:
        data["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return data


def chat_with_tools(
    user_input: str,
    history: list[dict] | None = None,
    verbose: bool = False,
) -> tuple[str, list[dict]]:
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    round_start = len(messages) - 1  # 含本轮 user，便于多轮 extend(history)

    while True:
        messages = trim_messages(messages)
        if verbose:
            print("[context]\n" + format_analysis(analyze_messages(messages)))

        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        mesg = resp.choices[0].message

        if verbose and resp.usage:
            u = resp.usage
            print(
                f"[usage] prompt={u.prompt_tokens}, "
                f"completion={u.completion_tokens}, total={u.total_tokens}"
            )

        messages.append(_assemble_messages(mesg))

        if not mesg.tool_calls:
            reply = mesg.content or ""
            return reply, messages[round_start:]

        for tool_call in mesg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            if verbose:
                print(f"\n🔧 {tool_name}({tool_args})")
            result = execute_tool(tool_name, tool_args)
            if verbose:
                preview = result if len(result) <= 200 else result[:200] + "..."
                print(f"📦 {preview}")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
