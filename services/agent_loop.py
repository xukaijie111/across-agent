import json

from services.context import analyze_messages, format_analysis, trim_messages
from services.llm import MODEL, client
from services.tools import TOOLS, execute_tool

SYSTEM_PROMPT = """你是一个多端小程序开发助手，熟悉 uni-app、Taro、Morjs。

## 执行任务
当用户提出检测、排错、改代码或构建类需求时，按以下步骤推进：

1. **先理解** — 用工具确认框架、相关文件、git 状态或构建错误；信息不够先问用户，不要猜测。
2. **再行动** — 给出最小必要改动或排查步骤；需要事实时调用工具，一次不够可继续调。
3. **再验证** — 对照用户原问题检查结论是否完整；检测/构建类结论必须以工具结果为准。

**出问题时：**
- 同一错误反复出现，停下来分析原因，不要重复同一种做法。
- 确实卡住时，说明卡点并请求用户补充信息或决策。

## 概念问答
当用户问概念、对比、用法、最佳实践，且不涉及当前项目具体文件或构建结果时：
- 先理清用户真正想问什么、涉及哪个框架/平台、有无前提条件。
- 回答时先给结论，再分点说明；需要对比时分项列差异。
- 若问题其实依赖当前项目（框架版本、目录结构、配置内容），不要凭经验猜，改用工具确认或先问用户。

## 工作方式
- 需要项目事实时，必须通过工具获取；不要编造结果。
- 工具返回 JSON 后，用中文简洁总结；ok: false 时说明原因与下一步。
- 多端问题先确认编译目标（微信/支付宝/H5/App），再给平台相关建议。

## 信息不足时
- 工具无法获取、结果不完整或仍不足以回答时，必须先向用户追问，补齐关键信息后再继续。
- 禁止在缺少依据时猜测路径、框架、平台、文件内容或构建结果。
- 目标或范围不清（如编译平台、要改哪些文件）时，先简短提问，不要擅自假设并动手。

## 与用户沟通
- 简洁直接，先给结论，再给关键细节；引用代码只贴相关片段。
- 较长任务可简短说明进度：已做了什么、接下来做什么。"""


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
