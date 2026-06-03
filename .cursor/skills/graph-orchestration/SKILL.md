---
name: graph-orchestration
description: >-
  CrossAgent LangGraph 编排层约定：类封装（State/Nodes/Graph/Orchestrator）、ReAct 图结构、
  依赖方向与手写优先。在用户讨论编排层、graph、LangGraph、run_turn、或要求重写 orchestration 时使用。
---

# Graph 编排层（类设计 + 手写优先）

> **编排层用类组织，代码默认只在对话框给用户手抄，不直接改仓库。**

---

## 1. 硬规则（手写优先）

| 场景 | 做法 |
|------|------|
| 用户要编排层 / graph / nodes 代码 | **对话框按文件给完整代码块**，不调用 Write / StrReplace |
| 用户问架构、怎么拆类 | 只讲解 + 对话框代码 |
| 用户明确说「写到文件里」「直接改项目」 | 才用编辑工具写 `services/graph/` |
| 用户说「写 skill / 写规则」 | 可写 `.cursor/skills/` |

**「再写一遍」「帮我写 xxx」≠ 授权写文件**，除非同时说了「写进项目」。

---

## 2. 类设计（必须遵守）

编排层用 **4 个类 + 1 个 TypedDict**，禁止全函数散落：

```text
AgentState (TypedDict)     — 图状态
AgentNodeRunner (class)    — agent / tools 两个节点逻辑
AgentGraphFactory (class)  — 建图、条件边
ChatOrchestrator (class)   — 对外入口 run_turn()
```

| 类 | 职责 | 禁止 |
|----|------|------|
| `AgentState` | `messages` + 可选 `verbose` | 不放 Session / DB |
| `AgentNodeRunner` | `call_model()` / `execute_tools()` | 不拼 system、不管 history 持久化 |
| `AgentGraphFactory` | `build()` → compiled graph | 不调 LLM 业务以外的存储 |
| `ChatOrchestrator` | 拼 messages → `invoke` → `(reply, delta)` | 不写 tool 注册逻辑 |

**依赖方向**：

```text
CLI / agent_loop → ChatOrchestrator → AgentGraphFactory → AgentNodeRunner
                                              ↓
                                    prompts/system, tools, llm, context
```

`agent_loop.py` 只做薄封装，ReAct 循环必须在 LangGraph 图里，不在 `while True`。

---

## 3. 目录结构

```text
services/
├── prompts/system.py       # SYSTEM_PROMPT
└── graph/
    ├── __init__.py         # 导出 ChatOrchestrator, run_turn
    ├── state.py            # AgentState
    ├── nodes.py            # AgentNodeRunner
    ├── graph.py            # AgentGraphFactory
    └── runner.py           # ChatOrchestrator
```

---

## 4. ReAct 图

```text
START → agent → 有 tool_calls? → tools → agent → … → END
                      ↓ 否
                     END
```

---

## 5. 对话框给代码的格式

1. 标明路径：`### services/graph/nodes.py`
2. 给**完整文件**内容，方便手抄
3. 说明**手写顺序**
4. 已有仓库代码用 citation；新代码用 markdown 代码块

---

## 6. 自检（给编排层代码前）

- [ ] 用户是否授权写文件？没有 → 只对话框
- [ ] 是否用类而非散落函数？
- [ ] `ChatOrchestrator` 是否薄（只编排，不实现 tool registry）？
- [ ] `get_tools()` 而非已废弃的 `TOOLS` 常量？

---

## 7. 一句话

> **编排层 = 类 + LangGraph ReAct；Agent 出卷，用户手抄交卷。**
