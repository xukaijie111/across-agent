# 徐先生 · 个人档案与 Agent 知识库

## 基本信息

- 姓名：徐开洁，男，38 岁，现居杭州
- 工作年限：约 13 年（研发相关 12 年+）
- 求职方向：Agent / AI 应用工程
- 技术标签：JavaScript、TypeScript、Node.js、Python、Agent 工程化

## 职业方向说明

- **2026 年 5 月起**：系统转向 Web + Agent（SSE 流式、编排、工具体系、可产品化落地）
- **2026 年 5 月之前**：十余年主线为嵌入式 → 前端 → 小程序多端架构，收钱吧期间任高级前端 / 前端架构师
- 并非「一年内仓促转型」：是在前端架构与工程化经验之上，延伸 Agent 工程化能力
- Agent Playground 等为 2026 年 5 月后的个人实践项目
- **近期在学习**：Agent 权限的合理设计（工具边界、人工审批、调用限额、敏感操作隔离）

## 个人优势（摘要）

- 研发路径从嵌入式软件到前端架构，具备跨层与系统性思维
- 能主导核心模块 0→1，推动工程规范、Code Review 与架构沉淀
- 深耕小程序多端工程、框架设计与复杂业务下的团队协作
- 2026 年 5 月起聚焦 Web + Agent：SSE 流式、编排、工具体系与可产品化的 Agent 落地
- 技术栈：JS / TS / Node（Express）/ Python；比较熟悉 LangChain

## 工作经历

### 上海收钱吧网络科技有限公司杭州分公司（2020.08 – 2026.05）

- 职位：高级前端工程师 / 前端架构师
- 工作：设计并迭代多端小程序架构；优化研发流程与多端编译；建立 Code Review 与架构分享机制
- 成果：从 0 搭建多端架构，统一研发规范，在快速交付与系统稳定性之间取得平衡

### 杭州盒研信息技术有限公司（2019.09 – 2020.08）

- 职位：前端开发
- 工作：支付宝/微信小程序、IOT 支付设备、小程序仓储系统

### 杭州看板网络科技有限公司（2017.07 – 2019.09）

- 职位：前端开发
- 工作：公司广告 SaaS 平台前端

### 杭州好猫数据有限公司（2013.03 – 2017.07）

- 职位：前端 Team Leader
- 工作：团队管理，toB / toC 前端研发

### 众海康集团有限公司（2015.03 – 2017.03，与上一段并行需以简历为准）

- 职位：前端 Team Leader
- 工作：模块研发、任务分配、质量把控、Code Review 与版本发布协调

### 浙江大华技术股份有限公司（2013.03 – 2015.03）

- 职位：嵌入式软件工程师
- 工作：NVR 产品内核驱动开发与维护、U-Boot 移植与维护
- 荣誉：2013 年度「优秀新员工」（解决关键内核驱动缺陷）

## 代表项目

### 小程序商城（2020.08 – 2026.05）

- 角色：架构师
- 背景：服务百万级商户的多端小程序，支持多团队并行开发
- 职责：统一技术与工程化底座；规范构建、发布与测试流程；核心模块兼顾高并发、可维护与可扩展
- 关键词：多端小程序、工程化、组件化、构建发布、团队协作

### Agent Playground（2026.05 起，个人实验项目，Python + Vue H5）

- 角色：独立设计与实现
- 背景：2026 年 5 月转向 Agent 后的综合实践；将多种业务 Agent（客服、SQL 问数、会议纪要、个人分身等）统一到 FastAPI + SSE Playground
- 职责：Runner 注册协议、会话持久化、上下文裁剪、RAG 文档问答
- 技术点：LangGraph 客服 HITL、LangChain SQL Agent、FAISS RAG、前端 rAF 流式渲染

## 教育经历

- 杭州电子科技大学 · 硕士 · 电路与系统（2010 – 2013）
- 杭州电子科技大学 · 本科 · 电子信息工程（2006 – 2010）

---

# 我对 Agent 与 LangChain 的理解

## 总体观点

- Agent 本质是「推理 + 行动」循环，现代实现多用 native tool calling，不必拘泥于文本版 ReAct 格式
- LangChain 1.x 把 Agent 能力收敛到 `create_agent` + Middleware 扩展，比早期 AgentExecutor 黑盒更易治理
- 我会把 Session（持久化）、Context（发给模型的 working view）、Memory（长期笔记）、Skill（人类规范）分层看待，避免混在一个 prompt 里
- 上下文治理应在调 LLM 前做瞬时裁剪，不要写回 checkpoint，否则历史会被污染

## Runnable 执行模型（langchain-core）

- `libs/langchain-core/src/runnables/` 是所有链路的底座
- 统一 `invoke` / `stream` / `batch` 入口，config 可透传（含 callback、tags、metadata）
- 理解 Runnable 后，Middleware 的 `wrapModelCall`、LLM 外包一层治理，都是同一套组合思想
- 协作式取消可看 `libs/langchain-core/src/utils/signal.ts` 的 `raceWithSignal` 模式

## Middleware 体系（langchain agents）

- 路径：`libs/langchain/src/agents/middleware/`，内置 15+ 中间件
- 钩子定义在 `libs/langchain/src/agents/middleware.ts`：`beforeModel`、`wrapModelCall`、`wrapToolCall` 等
- 我的实践对照：CrossAgent / Playground 里用 `make_chat_llm` 管道做上下文裁剪，相当于轻量版 `wrapModelCall` 前置治理

### 人工介入（HITL）

- 实现：`middleware/hitl.ts`，支持 `interruptOn` 指定哪些工具需人工审批
- 我的项目对照：服装客服 Agent 用 LangGraph `interrupt` + 前端 confirm/cancel，与 HITL 思想一致，但图编排在自己手里

### 工具筛选（llmToolSelector）

- 用小模型先筛一轮工具，降低主模型 tool schema token 压力
- 适合工具数量多、但单轮只需少数工具的场景

### 上下文治理（contextEditing）

- 清理过时或过大的 `ToolMessage`，缓解「重复读同一状态」导致的记忆污染
- 我的 Playground 已做历史 `trim_messages`；tool 结果裁剪与 dedup 留给插件槽位，思路与官方 middleware 对齐

### 摘要压缩（summarization）

- 历史超长时摘要旧轮次，保留最近对话
- 我用 LangChain `count_tokens_approximately` + `trim_messages(strategy="last")` 做 v1，摘要版可作 v2

### 调用限额（toolCallLimit）

- 限制工具调用次数，防刷、控成本
- 产品侧可配合 Runner 策略与前端确认流

### PII 脱敏（pii）

- 检测并脱敏个人敏感信息，适合客服、人事类 Agent
- 上线前需结合业务合规要求配置

## Agent 权限治理（近期关注）

- 我在探索：**Agent 能做什么、不能做什么、何时必须人确认**，怎样设计才合理、可落地
- 核心问题不是「给不给工具」，而是分层授权：
  - **工具可见性**：每个 Agent 只暴露必要工具（如 SQL 问数不给写操作、分身 Agent 无 tool）
  - **操作分级**：读 < 写 < 资金/隐私/不可逆操作，后两者走 HITL 或硬拦截
  - **调用限额**：`toolCallLimit` 防刷、控成本，避免模型陷入死循环调工具
  - **Runner 隔离**：Playground 里按 Agent 注册不同 Runner，权限策略跟着业务走，不混在一个黑盒里
- 与 Middleware 的关联：HITL、`toolCallLimit`、PII、llmToolSelector 都是权限治理的不同切面，不是单点方案
- Playground 现状：客服有退货确认 interrupt；SQL Agent 依赖只读库；其余 Agent 无工具——属于粗粒度权限拆分，细粒度策略还在学习中
- 个人倾向：权限默认收紧、按需放开；敏感动作可审计、可回放、可中断

## 我常怎么答 Agent 面试题

- ReAct vs Tool Calling：前者是教学/论文范式，后者是工程主流；关键都是「观测→再推理」
- Memory 不是魔法：多数是文件或 DB 读出后注入 prompt；要和 Session、Context 分开
- RAG 适合长文档、会更新的知识；短人设可放 system prompt
- 流式：后端应 `astream` 真 token 流；前端可 rAF 揭示缓冲，避免一次性刷屏

## 技术栈与熟练度（自评）

| 领域 | 程度 | 说明 |
|------|------|------|
| LangChain Middleware / create_agent | 比较熟 | 日常开发会用，读过部分源码，能对照设计 Playground 治理层 |
| LangGraph | 在用 | 客服 HITL、checkpoint |
| 小程序 / 前端架构 | 深 | 十余年主线 |
| Python FastAPI + SSE | 在用 | 当前 Agent 后端 |
| 向量 RAG（FAISS） | 在用 | 个人分身、文档问答场景 |
| Agent 权限治理 | 学习中 | 工具边界、HITL、调用限额、Runner 隔离 |
