# 千问（DashScope）LLM 接入

## 环境变量（`.env`）

```env
DASHSCOPE_API_KEY=sk-xxx
UPSTREAM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 可选
QWEN_MODEL=qwen-plus

# 本地代理（可选，用于日志/转发）
PROXY_HOST=127.0.0.1
PROXY_PORT=8765
```

> ⚠️ `.env` 已在 `.gitignore`，勿提交；Key 勿泄露。

---

## 接入方式：手写 OpenAI SDK（不用 LangChain）

DashScope **兼容 OpenAI API**，直接用 `openai` Python 包：

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url=os.environ.get(
        "UPSTREAM_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
)

response = client.chat.completions.create(
    model=os.getenv("QWEN_MODEL", "qwen-plus"),
    messages=[{"role": "user", "content": "你好"}],
)
```

加载 `.env`：

```python
from dotenv import load_dotenv
load_dotenv()
```

依赖：

```bash
pip install openai python-dotenv
```

---

## 两种连接方式

| 方式 | base_url | 适用 |
|------|----------|------|
| **A. 直连（推荐初学）** | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 最简单 |
| **B. 本地代理** | `http://127.0.0.1:8765/v1` | 统一日志、调试 |

---

## Tool Calling 手写模板

核心逻辑：`while` 循环，直到 LLM 不再返回 `tool_calls`。

```python
import json

def chat_with_tools(user_input: str) -> str:
    messages = [
        {"role": "system", "content": "你是多端小程序助手，需要时调用工具。"},
        {"role": "user", "content": user_input},
    ]

    while True:
        resp = client.chat.completions.create(
            model=os.getenv("QWEN_MODEL", "qwen-plus"),
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = resp.choices[0].message

        # 追加 assistant 消息（含 tool_calls）
        assistant_msg = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if not msg.tool_calls:
            return msg.content or ""

        for call in msg.tool_calls:
            result = execute_tool(
                call.function.name,
                json.loads(call.function.arguments),
            )
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })
```

---

## 模型选择

| 模型 | 用途 |
|------|------|
| `qwen-turbo` | 开发调试，便宜快 |
| `qwen-plus` | **默认推荐**，Tool Calling 稳定 |
| `qwen-max` | 复杂方案生成（design 阶段） |

---

## 流式（第二周再加）

```python
stream = client.chat.completions.create(
    model="qwen-plus",
    messages=messages,
    tools=TOOLS,
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        yield delta.content
```

> 流式 + Tool Calling 需拼接 `tool_calls` 分片，建议先非流式跑通循环。

---

## 与 LangGraph 的关系

```
千问 API
  ↑ 手写 openai SDK（services/llm.py + agent_loop.py）
LangGraph 编排（orchestration/graph.py）
  ↑ 节点里调用 agent_loop，不通过 LangChain Agent
```

**LLM 手写，编排 LangGraph，两者分离。**
