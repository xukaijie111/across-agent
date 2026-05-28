# CrossAgent 架构说明

## 一、分层

```
┌─────────────────────────────────────────┐
│  展示层（Next.js）                        │  聊天 / Spec轨 / 构建终端 / Eval
└──────────────────┬──────────────────────┘
                   │ HTTP / SSE
┌──────────────────▼──────────────────────┐
│  API 层（FastAPI）                        │  路由、鉴权、SSE
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  ★ 编排层（LangGraph）★                   │  阶段、分支、确认门、失败回流
└──────────────────┬──────────────────────┘
                   │ 调用
     ┌─────────────┼─────────────┬─────────────┐
     ▼             ▼             ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ LLM     │ │ OpenSpec│ │ Build   │ │ RAG     │
│ Service │ │ IO      │ │ Service │ │ Service │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

| 层 | 职责 | 实现 |
|----|------|------|
| 编排层 | 谁先谁后、何时暂停、失败走哪 | LangGraph `graph.py` |
| 节点 | 薄封装，调 Service | `orchestration/nodes/` |
| Service | LLM、RAG、构建、读写 spec | `services/` |
| 展示层 | 流式 UI、构建日志、Trace | Next.js |

**编排层独立** = 编排层不包含 LLM/构建实现，只通过调用 Service 驱动。

---

## 二、编排 = 工作流 + Agent 节点

- **工作流部分**：OpenSpec 五阶段、确认门、条件分支（LangGraph 边）
- **Agent 部分**：LLM 生成 proposal/design、implement 里 ReAct 选工具

```
硬工作流：propose → 确认 → design → 批准 → implement → archive
软 Agent：implement 内 LLM 决定 read_file / run_build / patch_file
```

---

## 三、OpenSpec 五阶段

```
产品需求 → 任务分解 → 需求确认 → 技术方案 → 实施(含构建) → 归档
   │          │          │          │          │          │
 proposal   tasks     confirm    design      apply     archive
```

目录结构：

```
openspec/
├── specs/                    # 系统现状（真相来源）
│   └── miniprogram/spec.md
└── changes/
    └── add-share-card/
        ├── proposal.md
        ├── requirements.md
        ├── design.md
        ├── tasks.md
        ├── specs/            # Delta: ADDED/MODIFIED/REMOVED
        └── status.yaml
```

---

## 四、LLM 与 LangGraph 分工

| 模块 | 用什么 | 说明 |
|------|--------|------|
| LLM 调用 + Tool 循环 | **手写**（openai SDK + 千问） | `services/agent_loop.py` |
| 阶段编排 | **LangGraph** | `orchestration/graph.py` |
| LangChain Agent | **不用** | 黑盒，不利于调试和面试 |

LangGraph 节点示例：

```python
async def implement_node(state):
    reply = await agent_loop.chat_with_tools(state["task"])
    logs = [line async for line in build_service.run_build(...)]
    return {"reply": reply, "build_logs": logs}
```

---

## 五、界面布局

```
┌────────────────────────────────────────────────────────────────────┐
│ CrossAgent │ Change: xxx │ 阶段: 方案 ▼ │ [确认并进入下一阶段]      │
├──────────────┬─────────────────────────────┬─────────────────────────┤
│ 💬 对话       │ 📋 Spec 轨（OpenSpec）        │ 🔨 构建流水线              │
│              │ proposal / design / tasks    │ detect→install→compile  │
├──────────────┴─────────────────────────────┴─────────────────────────┤
│ Engineering: Eval │ Trace │ Token │ MCP │ Git                       │
└────────────────────────────────────────────────────────────────────┘
```

---

## 六、Demo 参考

`demo/orchestration_demo/` 演示了编排层最小实现：

```bash
cd demo/orchestration_demo
pip install langgraph langchain-core typing_extensions
python main.py
```

- `orchestration/graph.py` — 编排规则（节点 + 边）
- `orchestration/nodes.py` — 薄节点，调 Service
- `services/` — LLM、OpenSpec IO、Build（mock）
