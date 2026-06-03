---
name: langchain-source
description: >-
  LangChain Python  monorepo 本地源码参考（路径 open-source/langchain-master）。
  说明 libs 分包结构、create_agent、AgentMiddleware 钩子、内置 middleware、
  langchain-core 抽象，供 CrossAgent 对照 Agent 循环 / Context / 未来 LangGraph 接入。
  在用户讨论 LangChain、create_agent、middleware、messages/tools 抽象或读本地源码时使用。
---

# LangChain 本地源码参考

> 源码路径：`/Users/xukaijie/Desktop/open-source/langchain-master`  
> 维护中的包：`libs/langchain_v1/`（PyPI 包名 `langchain`）  
> 基础抽象：`libs/core/`（PyPI 包名 `langchain-core`）  
> 集成：`libs/partners/`（openai、anthropic、ollama…）  
> 遗留：`libs/langchain/langchain_classic/`（不再加新功能）

CrossAgent **不必引入 LangChain 全家桶**；读源码是为了理解 Agent / Middleware / Message 分层，对照手写 `agent_loop` 与未来 LangGraph 接入。更高层封装见 `.cursor/skills/deepagents-tool-layer/`（Deep Agents 基于本仓库的 `create_agent`）。

---

## 1. Monorepo 结构（来自仓库 `AGENTS.md`）

```text
langchain-master/
├── libs/
│   ├── core/              # langchain-core：Message、Tool、Runnable 等协议
│   ├── langchain_v1/      # langchain：create_agent、内置 middleware
│   ├── langchain/         # langchain-classic（legacy）
│   ├── partners/          # 各模型/向量库集成
│   ├── text-splitters/
│   ├── standard-tests/
│   └── model-profiles/
├── examples/
└── AGENTS.md              # 仓库级开发指南（monorepo、测试、PR 规范）
```

**开发命令**（在 monorepo 根目录）：

```bash
uv sync --all-groups   # 装齐 editable 包
make test              # 单元测试
make lint && make format
```

---

## 2. 三层依赖关系

| 层 | 包 | CrossAgent 对应 |
|----|-----|-----------------|
| **Core** | `langchain-core` | messages 格式、tool schema、`trim_messages` 思路 |
| **LangChain** | `langchain` v1 | `create_agent` + middleware 栈（Deep Agents 也用） |
| **Partners** | `langchain-openai` 等 | 你们用 OpenAI 兼容千问时可对照 adapter |

Core 路径：`libs/core/langchain_core/`

| 子目录 | 内容 |
|--------|------|
| `messages/` | `HumanMessage`、`AIMessage`、`ToolMessage`、`SystemMessage` |
| `tools/` | `BaseTool`、`@tool`、tool call 结构 |
| `language_models/` | `BaseChatModel`、`invoke` / `stream` |
| `runnables/` | LCEL 组合（Chain 底层） |
| `messages/utils.py` | `trim_messages`、`count_tokens_approximately` |

LangChain v1 Agent 路径：`libs/langchain_v1/langchain/agents/`

| 文件 | 职责 |
|------|------|
| `factory.py` | **`create_agent()`**：组装 LangGraph StateGraph + middleware 栈 |
| `middleware/types.py` | **`AgentMiddleware`** 基类、`ModelRequest` / `ModelResponse` |
| `middleware/*.py` | 内置 middleware（见 §4） |
| `structured_output.py` | 结构化输出策略 |

---

## 3. Agent 入口：`create_agent`

```python
from langchain.agents import create_agent

graph = create_agent(
    model=...,
    tools=[...],
    middleware=[...],
    checkpointer=...,   # LangGraph 线程持久化（≈ CrossAgent Session）
    system_prompt=...,
)
```

实现：`libs/langchain_v1/langchain/agents/factory.py`

- 底层是 **LangGraph `StateGraph`**，不是简单 while 循环
- `middleware` 按顺序注册为 graph 节点
- `checkpointer` 持久化 **对话 state（messages）**，不是 Deep Agents 那种 `AGENTS.md` 长期记忆

**与 CrossAgent 手写 loop 的对照：**

| LangChain | CrossAgent 现在 |
|-----------|-----------------|
| `create_agent` + LangGraph | `services/agent_loop.py` 手写 while + tool call |
| `checkpointer` | `SessionService` + SQLite messages |
| `SummarizationMiddleware` | `services/context.py` `trim_messages` |
| `MemoryMiddleware`（在 **deepagents** 里，不在 langchain 核心） | `services/memory/` v2 长期记忆文件 |

---

## 4. `AgentMiddleware` 钩子

定义：`libs/langchain_v1/langchain/agents/middleware/types.py`

| 钩子 | 时机 | 典型用途 |
|------|------|----------|
| `before_agent` / `abefore_agent` | agent 开始前 | 加载外部 context（Deep Agents Memory 在这） |
| `before_model` / `abefore_model` | 每次调 LLM 前 | 改 messages、注入 tools |
| `wrap_model_call` / `awrap_model_call` | 包裹 LLM 调用 | 重试、缓存、改 request/response |
| `after_model` / `aafter_model` | LLM 返回后 | 解析、限流 |
| `wrap_tool_call` / `awrap_tool_call` | 包裹 tool 执行 | 权限、HITL、重试 |
| `after_agent` / `aafter_agent` | agent 结束后 | 清理、日志 |

`ModelRequest` 字段（middleware 可改）：`model`、`system_message`、`messages`、`tools`、`tool_choice`、`state`。

装饰器写法（不必 subclass）：`@before_agent`、`@wrap_model_call`、`@wrap_tool_call` 等同文件底部。

---

## 5. LangChain 内置 middleware（v1）

目录：`libs/langchain_v1/langchain/agents/middleware/`

| 文件 | 作用 |
|------|------|
| `summarization.py` | token 超阈值时 **摘要压缩** history（≈ Context 层高级版） |
| `context_editing.py` | 编辑即将发给模型的 context |
| `human_in_the_loop.py` | 指定 tool 执行前人工确认 |
| `tool_call_limit.py` / `model_call_limit.py` | 调用次数上限 |
| `tool_retry.py` / `model_retry.py` / `tool_emulator.py` | 重试与模拟 |
| `tool_selection.py` | 动态选工具子集 |
| `todo.py` | Todo 列表 middleware |
| `pii.py` | PII 检测/脱敏 |
| `shell_tool.py` | shell 工具相关 |
| `file_search.py` | 文件搜索 |
| `model_fallback.py` | 模型降级 |

**注意**：LangChain 核心 **没有** `MemoryMiddleware`。长期记忆（`AGENTS.md`）在 **Deep Agents** 仓库：`deepagents/middleware/memory.py`。

---

## 6. Memory / Session / Context 三分（读源码时别混）

| 概念 | LangChain 生态里谁管 | 存什么 |
|------|----------------------|--------|
| **Session / Checkpoint** | `create_agent(checkpointer=...)` + LangGraph | 线程 messages、tool 结果 |
| **Context 裁剪** | `SummarizationMiddleware` 或 core `trim_messages` | 控制发给模型的 token |
| **Memory（长期）** | Deep Agents `MemoryMiddleware` | `AGENTS.md` 文件，注入 system prompt |

CrossAgent 分层应对齐此边界，见 `services/session.py`（session）、`services/context.py`（context）、`services/memory/`（v2 长期记忆）。

---

## 7. Partners 集成（千问 / OpenAI 兼容）

路径：`libs/partners/`

| 目录 | 包 |
|------|-----|
| `openai/` | `langchain-openai` |
| `anthropic/` | `langchain-anthropic` |
| `ollama/` | 本地模型 |
| `qdrant/`、`chroma/` | 向量库（RAG 用） |

CrossAgent 当前直接用 OpenAI SDK（`services/llm.py`），不必迁 partners；接 LangGraph 时可再评估。

---

## 8. 建议阅读顺序（对照 CrossAgent）

1. `libs/core/langchain_core/messages/` — message 协议（与你们 SQLite 存的 dict 对齐）
2. `libs/core/langchain_core/tools/` — tool schema 与 `ToolMessage`
3. `libs/langchain_v1/langchain/agents/factory.py` — `create_agent` 如何拼 graph（前 200 行 + middleware 注册段）
4. `libs/langchain_v1/langchain/agents/middleware/types.py` — `AgentMiddleware` 全文扫一遍
5. `libs/langchain_v1/langchain/agents/middleware/summarization.py` — 摘要 vs 你们 `trim_messages`
6. `../deepagents-main/libs/deepagents/deepagents/graph.py` — Deep Agents 如何在 `create_agent` 外包 middleware 栈

---

## 9. CrossAgent 借鉴 vs 不借鉴

**可借鉴：**

- Middleware 钩子划分（before_model / wrap_tool_call）
- `ModelRequest` 统一改 tools / system / messages
- Summarization 作为独立 middleware，不混进 Memory

**不照搬：**

- 整个 LangGraph StateGraph（v1 继续手写 loop 即可）
- langchain-classic 遗留 API
- 全量 partners 依赖

目标形态（与 deepagents skill 一致）：

```text
Provider → ToolRegistry → Context(trim) → agent_loop → Session(存 messages)
                                              ↑
                                    Memory v2（长期文件，可选注入 prompt）
```

---

## 10. 相关本地源码

| 仓库 | 路径 | 关系 |
|------|------|------|
| LangChain | `/Users/xukaijie/Desktop/open-source/langchain-master` | 本文 |
| Deep Agents | `/Users/xukaijie/Desktop/open-source/deepagents-main` | 基于 LangChain `create_agent` |
| LangGraph | 独立仓库（本 monorepo 通过依赖引用） | checkpoint / StateGraph |

文档站：[docs.langchain.com](https://docs.langchain.com/oss/python/langchain/overview) · API：[reference.langchain.com/python](https://reference.langchain.com/python)
