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

> 面向访客/面试官：这是我 2026 年 5 月转向 Agent 后的**综合实践作品**，用一套 Playground 把多种典型 Agent 场景跑通，并沉淀可复用的工程骨架。

#### 项目目标

- 把「聊天、RAG 客服、SQL 问数、会议纪要、个人分身」等常见 Agent 形态放在**同一套调试台**里对比体验
- 验证自己对 Agent 工程化的理解：Runner 注册、会话持久化、SSE 流式、上下文治理、HITL、权限粗拆
- 可部署对外演示（阿里云 ECS + Nginx），而不只是本地脚本

#### 整体架构（我做了什么）

```text
Vue H5 调试台（侧栏选 Agent、聊天、历史会话、确认中断）
        │  HTTP / SSE
FastAPI 统一 API（/api/agents、/api/sessions、/api/chat/stream）
        │
Runner 层（每个 Agent 一个 Runner，实现 stream_turn / stream_resume）
        │
subagents/（各业务 agent.py：客服图、SQL 循环、RAG 流水线等）
        │
基础设施：MySQL 会话与消息、百炼/OpenAI 兼容 LLM、FAISS 向量库
```

- **子 Agent 隔离**：业务逻辑在 `server/subagents/<name>/agent.py`，不堆在一个大文件里
- **Runner 桥接**：`server/runners/` 把 subagent 适配成统一 `StreamEvent` 协议，API 层无业务 if-else
- **注册发现**：`registry.load_runners()` 启动时注册；前端 `GET /api/agents` 动态拉列表
- **会话持久化**：MySQL 存 session / message；`persona`、`echo` 等支持多轮历史恢复
- **统一上下文治理**：`make_chat_llm(govern=True)` 在调模型前裁剪历史；**只裁 working view，不写回 DB/checkpoint**
- **流式体验**：后端 SSE 推送 delta；前端 `requestAnimationFrame` 逐字揭示，发送后输入框保持聚焦
- **一键部署**：`scripts/deploy-aliyun.sh` 打包上传 ECS，远程构建前端并重启 systemd

#### 当前已上线的子 Agent（以本仓库为准）

| Runner id | 名称 | 演示什么场景 | 是否用 Tool | 我采用的实现 |
|-----------|------|--------------|-------------|--------------|
| `persona` | 我的分身 | 个人知识 RAG、履历与技术面问答 | 否 | FAISS + `knowledge.md`；第一人称；侧栏默认排第一 |
| `customer-support` | 服装客服 | 电商 RAG 客服 + 敏感操作需人确认 | 是 | LangGraph 图编排；FAISS 知识库；退货 `interrupt` + 前端 confirm/cancel |
| `echo` | 聊天助手 | 最简对话基线，无工具无 RAG | 否 | LangGraph 单节点 `chat`；不联网、不确定不编造 |
| `meeting-notes` | 会议纪要 | 长文本 → 结构化 Markdown 输出 | 否 | 单次 prompt 生成摘要/决策/待办；前端支持 Markdown 渲染 |
| `sql-query` | 数据问数 | 自然语言查结构化数据 | 是 | LangChain `SQLDatabaseToolkit` + 只读 MySQL demo 库（客户/商品/订单） |

**各 Agent 补充说明（方便他人了解细节）：**

- **我的分身**：内置 `knowledge.md`（简历、职业转向、LangChain 理解、Playground 说明）；仅依据资料回答，避免编造
- **服装客服**：模拟「衣汇商城」；用户要求退货时会触发 HITL，必须点确认才继续执行工具
- **聊天助手**：用来对比「纯 LLM 对话」与「带 RAG/工具的 Agent」差异
- **会议纪要**：输入口适合粘贴长文字稿；输出为可复制的结构化纪要
- **数据问数**：演示 Text-to-SQL；数据库为 demo 电商 schema，强调只读与安全边界

- **已下线**：`pdf-qa`（文档问答）已被 `persona` 替代，目录保留但未注册
- **权限粗拆**：有 tool 的仅客服、SQL；分身/聊天/会议纪要无 tool calling——我在探索更细粒度权限前的第一阶段做法

#### 工程亮点（可问可聊）

- Session / Context / Memory 分层：DB 存全量历史，发给模型前瞬时裁剪
- 上下文治理插件槽位：`server/context/` 统一注册，子 Agent 不各自调插件
- 客服 HITL 与 LangChain `middleware/hitl.ts` 思想对照：我用 LangGraph `interrupt` 自管图与 checkpoint
- 部署可复现：ECS + Nginx 反代 + systemd 守护 `agent-api`；增量更新 `make deploy-update`

#### 演示访问

- 公网演示（IP）：http://106.15.5.36
- API 文档：http://106.15.5.36/docs
- 域名 `agentnow.fun` 已解析，但大陆访问需 ICP 备案，备案前请用 IP

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
- Playground 现状（详见上文子 Agent 表）：客服有退货确认 interrupt；SQL 只读库 + 内置 toolkit；persona/echo/meeting-notes 无工具——粗粒度权限拆分，细粒度策略还在学习中
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
