# Agent 入门 & 框架 · 复盘题库

> 来源：学习视频截图整理  
> 用途：后续逐题自答、对照 CrossAgent 项目、面试前快速过一遍  
> 相关：[interview-xhs-ai-coding.md](./interview-xhs-ai-coding.md) · [architecture.md](./architecture.md)

---

## 使用方式

1. 每题先 **口头答 2 分钟**，再对照下方「CrossAgent 映射」补缺口  
2. 答完的题在 `[ ]` 里打 `x`：`[x]`  
3. 项目里还没有的能力标 ⏳，已在项目里标 ✅

---

## 一、Agent 入门 10 题

- [ ] **Q1.** 什么是大模型 Agent？它与传统的 AI 系统有什么不同？

  **CrossAgent 映射：** ReAct Agent（`services/graph/`）vs 传统规则/单轮 QA；有 Tool Calling、多轮 state、编排图。

- [ ] **Q2.** LLM Agent 的基本架构有哪些组成部分？

  **CrossAgent 映射：** LLM（`services/llm.py`）+ System Prompt + Tools（`services/tools/`）+ 编排（LangGraph）+ Session（`services/session.py`）+ 前端（`apps/web`）。

- [ ] **Q3.** LLM Agent 如何进行决策？能否使用具体的方法解释？

  **CrossAgent 映射：** ReAct — `call_model` → `tool_calls?` → `execute_tools` → 再 `call_model`；`route_after_agent` 条件边。

- [ ] **Q4.** 如何让 LLM Agent 具备长期记忆能力？

  **CrossAgent 映射：** ⏳ Week 1 仅 Session 存 messages；v2 计划 Memory 文件 / 摘要（见 learning-plan）。

- [ ] **Q5.** LLM Agent 如何进行动态 API 调用？

  **CrossAgent 映射：** Tool Registry + `@tool`；MCP 外部工具（`mcp_provider.py`）；模型 `tool_choice="auto"` 动态选工具。

- [ ] **Q6.** LLM Agent 在多模态任务中如何执行推理？

  **CrossAgent 映射：** ⏳ 当前纯文本；可答 vision tool / 图片 URL + Markdown 渲染 / 多模态 model。

- [ ] **Q7.** LLM Agent 有哪些局限性？

  **可答要点：** 幻觉、上下文窗口、工具误调、延迟与成本、安全（越权读写）、Eval 不稳定。

- [ ] **Q8.** 如何衡量 LLM Agent 的性能？

  **CrossAgent 映射：** ⏳ Eval 15 cases（learning-plan Week 3）；Trace、成功率、延迟、人工抽检。

- [ ] **Q9.** 未来 LLM Agent 可能有哪些技术突破？

  **可答要点：** 更长上下文、多 Agent 协作、更强 reasoning model、端侧小模型、标准化 MCP、自动 Eval。

- [ ] **Q10.** 请你设计一个 LLM Agent，用于医学问答，它需要具备什么？

  **可答要点：** 免责声明 + 不替代医生；RAG 权威文献；低温度 + 引用来源；敏感词/HITL；不做诊断只给科普；审计日志。

---

## 二、主流 Agent 框架 10 题

> 原题列表从 Q2 起编号，此处按 Q1–Q9 重排便于复盘；内容与截图一致。

- [ ] **Q1.** LangChain 的核心组件有哪些？

  **可答要点：** Messages、Tools、Runnable、Prompt、Output Parser、Retrievers、Callbacks；CrossAgent 用 `langchain-core` 的 `@tool`，编排手写 LangGraph。

- [ ] **Q2.** LangChain Agent 的主要类型有哪些？

  **可答要点：** ReAct、OpenAI Functions、Structured Chat；CrossAgent 是 **ReAct + Tool Calling**。

- [ ] **Q3.** LlamaIndex 如何与 LangChain 结合？

  **可答要点：** LlamaIndex 管索引/RAG，LangChain 管 Agent 链；QueryEngine 作 LangChain Tool。

- [ ] **Q4.** AutoGPT 如何实现自主决策？

  **可答要点：** 目标分解 + 循环（思考→选工具→执行→观察）；与 ReAct 类似但更长自主链、易漂移。

- [ ] **Q5.** BabyAGI 如何进行任务管理？

  **可答要点：** 任务队列 + 优先级 + 创建/完成/衍生子任务；类似 Planner 节点。

- [ ] **Q6.** CrewAI 如何管理多个 Agent 之间的协作？

  **可答要点：** Role / Goal / Backstory；顺序或层级流程；任务委派与汇总。

- [ ] **Q7.** LangChain 如何支持 API 调用？

  **可答要点：** `@tool` / `StructuredTool` / OpenAI function schema；CrossAgent `get_tools()` + `convert_to_openai_tool`。

- [ ] **Q8.** 如何优化 LLM Agent 的性能？

  **可答要点：** 上下文裁剪（`trim_messages` ✅）、并行 tool、缓存、小模型路由、流式 SSE、超时与截断 ⏳。

- [ ] **Q9.** LLM Agent 在企业应用中的典型场景有哪些？

  **可答要点：** 客服、代码助手（CrossAgent ✅）、数据分析、工单、知识库问答、Ops 自动化。

---

## 三、与 CrossAgent 进度对照（速查）

| 主题 | 项目现状 |
|------|----------|
| ReAct 编排 | ✅ `services/graph/` |
| Tool Calling | ✅ 10 tools |
| SSE 流式 Web | ⏳ `api/main.py` + `.env.local` 联调 |
| Session 持久化 | ⏳ 部分 |
| 长期 Memory | ⏳ v2 |
| RAG | ⏳ |
| Eval / Trace | ⏳ Week 2–3 |
| 多 Agent | ⏳ |

---

## 四、复盘记录（自填）

| 日期 | 复习范围 | 薄弱题号 | 下一步 |
|------|----------|----------|--------|
| | | | |
