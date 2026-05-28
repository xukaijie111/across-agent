# Agent 全栈 · 1 个月学习规划

> 背景：资深前端架构师 → Agent 全栈工程师  
> 目标：1 个月内产出 **CrossAgent** 成品，能打动面试官  
> 项目：多端小程序 Agent 工作台（聊天 + OpenSpec 需求流 + 构建可视化 + Eval/Trace）

---

## 一、学习原则

1. **只做一个项目**（CrossAgent），所有学习都围绕它展开  
2. **70% 写代码，30% 看概念** —— 不要并行开太多理论线  
3. **LLM + Tool 手写，编排用 LangGraph，不用 LangChain Agent**  
4. **前端长板要发挥**：流式 UI、构建终端、Spec 轨、Trace 回放  
5. **1 个月的「精通」= 有 Demo、有数据、能讲 trade-off**，不是读完框架源码  

---

## 二、学习顺序（严格按序）

```
① LLM API + Tool Calling     （2 天）  ← 从这里开始
② Context 工程               （2 天）
③ 编排（LangGraph）           （3 天）
④ RAG                        （3 天）
⑤ MCP                        （2 天）
⑥ Eval + Trace               （第 2～4 周持续）
```

### ① LLM API + Tool Calling（第 1～2 天）⭐ 当前阶段

**学什么**

- Chat Completions / Messages API（OpenAI 兼容格式）
- 流式 `stream=True` + SSE 推前端
- Function Calling：`tools` schema + `tool_calls` 循环
- 手写 `while` 循环：调 LLM → 执行 tool → 结果塞回 messages → 再调 LLM

**不学什么**

- LangChain `AgentExecutor` / `create_tool_calling_agent`
- Transformer 原理、模型训练
- LangGraph（这阶段还不需要）

**验收标准**

```
用户输入 → 组装 messages → 调千问 API → 有 tool_call 则执行 → 最终回复
```

**产出**

- `services/llm.py` — 千问客户端
- `services/tools.py` — tool schema + execute_tool
- `services/agent_loop.py` — chat_with_tools() 循环
- FastAPI `/chat` + Next.js 流式聊天页（2 个 mock 工具：`detect_framework`、`run_build`）

**详见** [qwen-setup.md](./qwen-setup.md)

---

### ② Context 工程（第 3～4 天）

**学什么**

- message 四类角色：system / user / assistant / tool
- Context 组成：system + 历史 + RAG 片段 + tool 结果 + 当前输入
- 超 Token 裁剪策略：先裁旧 tool 结果 → 摘要历史 → 减少 RAG chunk
- 构建日志 5000 行 → 只提取 error 行 + 上下文再给 LLM

**验收标准**

- 能回答：「一次请求的 Context 怎么拼？超了先裁什么？」
- UI 底部展示 Token 组成（system / history / tool 各多少）

**产出**

- Context 组装函数 `build_messages(state)`
- 聊天页 Token 统计面板

---

### ③ 编排 · LangGraph（第 5～7 天）

**学什么**

- `StateGraph`、节点、边、`conditional_edges`
- OpenSpec 五阶段硬编排：propose → 确认 → design → 批准 → implement → archive
- checkpoint + interrupt（人工确认门）
- implement 子图内 ReAct tool 循环（混合编排）

**不学什么**

- LangChain 全家桶链路
- LangGraph 源码

**验收标准**

- 未确认 proposal 时不进入 design
- 未批准 design 时不执行 build
- 每个节点 < 50 行，只调 Service

**产出**

- 升级 `demo/orchestration_demo` 为真实 CrossAgent 编排层
- 中间 Spec 轨 UI + 阶段条

**详见** [architecture.md](./architecture.md)

---

### ④ RAG（第 8～10 天）

**学什么**

- 文档切分 → Embedding → 向量存储 → 检索 → 注入 prompt
- chunk size / overlap / TopK 调优
- 失败模式：召不回、召错、幻觉引用

**验收标准**

- 灌入 Taro/uni-app 文档，问「微信分享 API」能引用正确片段
- Eval 至少 5 条 RAG 相关用例

**产出**

- pgvector 检索服务
- 文档上传 + 引用来源展示 UI

---

### ⑤ MCP（第 11～12 天）

**学什么**

- MCP server / client 概念
- 把 `read_file`、`run_build` 封装为 MCP tool
- 工具权限：读 vs 写 vs 构建

**验收标准**

- Agent 通过 MCP 调用至少 2 个工具
- Settings 页展示已连接 MCP tools

**产出**

- 自建 MCP server（filesystem + build）

---

### ⑥ Eval + Trace（第 2～4 周持续）

**学什么**

- Trace：每步 input / output / latency / tokens
- Eval：固定测试集 + pass rate + prompt 版本对比
- 轨迹回放 UI

**验收标准**

- 20 条 Eval（需求分解 + 构建排错）
- 改 prompt 前后 pass rate 可对比、有截图

**产出**

- Traces / Eval Tab（**面试差异化**）

---

## 三、第 1 个月不学的（除非改投架构岗）

| 暂缓 | 原因 |
|------|------|
| Multi-Agent 复杂协作 | 单 Graph + 子图够用 |
| 微调 SFT / LoRA | 应用岗非必须 |
| K8s 深入 | Docker Compose 够用 |
| Dify / Coze 平台 | 时间不够，自研更深 |
| LangChain Agent 封装 | 黑盒，不利于理解和面试 |
| Transformer / 分布式训练 | AI 架构师岗才需要 |

---

## 四、CrossAgent 四周项目排期

| 周 | Agent 后端 | 前端同步 |
|----|-----------|----------|
| **W1** | 千问 Tool Calling + FastAPI SSE + OpenSpec proposal | 流式聊天 + tool 状态卡片 |
| **W2** | Context 裁剪 + LangGraph 五阶段 + 确认门 | Spec 轨 + 阶段条 |
| **W3** | RAG + Docker 沙箱构建 + 日志 SSE | 构建终端 xterm + 阶段 Stepper |
| **W4** | MCP + Eval + Trace + Docker 部署 | Trace 回放 + Eval 面板 + 录屏 |

---

## 五、技术栈

```
Frontend:  Next.js 14 + TypeScript + Tailwind + shadcn/ui + xterm.js
Backend:   Python 3.11 + FastAPI
LLM:       通义千问 DashScope（OpenAI 兼容 API，手写 SDK）
Agent:     手写 Tool Loop + LangGraph（仅编排层）
Vector:    PostgreSQL + pgvector
Tools:     MCP（filesystem + build）
Deploy:    Docker Compose
Spec:      OpenSpec 目录结构（openspec/specs + openspec/changes）
```

---

## 六、目录结构（目标）

```
python-less/
├── apps/
│   ├── web/                 # Next.js
│   └── agent/               # FastAPI
├── services/
│   ├── llm.py               # 千问客户端
│   ├── tools.py             # tool schema + 执行
│   ├── agent_loop.py        # Tool Calling 循环
│   ├── rag.py
│   └── build.py
├── orchestration/
│   ├── graph.py             # LangGraph 编排层
│   └── nodes/
├── openspec/
│   ├── specs/
│   └── changes/
├── demo/
│   └── orchestration_demo/  # 编排层 Demo（已完成）
└── docs/
```

---

## 七、前端 vs 后端学习配合

| 顺序 | 后端/Agent | 前端（你的长板） |
|------|-----------|-----------------|
| ① | LLM + Tool | 流式聊天 UI |
| ② | Context | Token 组成面板 |
| ③ | LangGraph | Spec 轨 + 阶段条 |
| ④ | RAG | 文档上传 + 引用来源 |
| ⑤ | MCP | 工具列表 Settings |
| ⑥ | Eval/Trace | 时间线回放 UI |

**不要等后端全做完再写前端** —— 每学一块，当天接 UI。

---

## 八、JD 能力对照（1 个月要「讲得深」的）

| 能力 | 项目体现 |
|------|----------|
| Context 工程 | Token 面板 + 日志摘要策略 |
| RAG | 多端文档库 + Eval |
| Tool / MCP | detect_framework / run_build / patch_file |
| 编排 | OpenSpec 五阶段 LangGraph |
| Eval / Trace | 20 条用例 + 回放 UI |
| Prompt | proposal/design 分阶段 prompt + 版本对比 |

---

## 九、面试话术（30 秒）

> 我是前端架构背景，做了 CrossAgent —— 多端小程序 Agent 工作台。产品需求走 OpenSpec 五阶段（proposal → 确认 → design → 实施），LangGraph 做硬编排 + 人工确认门，implement 里手写 Tool Calling 调千问。右侧实时展示 Taro/uni-app 构建日志，带 Eval 和 Trace 证明 Agent 可靠性。

---

## 十、今天可开始的 3 件事

1. 建 `services/llm.py` + `agent_loop.py`，读 `.env` 调千问  
2. FastAPI `/chat` 非流式 + 2 个 mock tool，跑通循环  
3. 准备 Taro/uni-app 文档 Markdown（后续 RAG 用）

---

## 十一、相关文档

- [architecture.md](./architecture.md) — 编排层 / Service / 工作流关系  
- [qwen-setup.md](./qwen-setup.md) — 千问 API 与 Tool Calling 配置  
- `demo/orchestration_demo/` — LangGraph 编排 Demo（可运行）
