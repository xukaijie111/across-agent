# 小红书 AI Coding 前端面试题 · 复盘文档

> 来源：小红书创新前端 · AI Coding / AI Agent 方向（一面～HR 面）  
> 用途：面试复盘 + 对照 CrossAgent 项目哪些题会碰到、哪些还没做  
> **主战场：Web（Next.js + SSE）**；CLI 仅调试/备用，不作为产品入口。

---

## 和 CrossAgent 的关系（总览 · Web 为主）

CrossAgent 是 **Web AI Coding 工作台 + 小程序 Agent 后端**：

```text
apps/web（Next.js）          ← 主入口：聊天 UI、Tool 卡片、SSE、未来 diff/确认
    ↓ POST /api/chat/stream（目标：FastAPI；当前 mock）
services/graph（LangGraph） ← ReAct 编排
services/tools              ← 读文件 / git / 构建
```

不是 RN 活动页，但 **小红书 AI Coding 前端面试题与 Web 侧高度重合**（流式、Tool UI、安全渲染、确认门、性能）。

| 面试题领域 | Web 会不会碰到 | 项目里对应什么 |
|-----------|----------------|----------------|
| 聊天 UI / 状态拆分 | ✅ 核心 | `ChatPage`、`useAgentChat`、`MessageList` |
| Tool 调用可视化 | ✅ 核心 | `ToolCard`、`tool_start` / `tool_end` SSE |
| 流式输出 / 长列表性能 | ✅ 核心 | `streamChat`、`applyEvent` 增量更新 |
| Markdown 安全渲染 | ✅ 核心 | `MessageBubble`（待加固） |
| Diff / 确认 / 回滚 | ✅ 会 | 未来侧边栏 + `write_file` 确认门 |
| Agent 权限 / HITL | ✅ 会 | middleware + Web 确认弹窗 |
| Prompt / Skill 编辑 | ✅ 会 | 运营向设置页（未做） |
| RAG 引用展示 | ⚠️ 计划 | 学习路线有，未做 |
| RN 组件 / Flutter 三端 | ❌ 弱相关 | 业务是小程序，不是 RN |
| CLI | ⚠️ 调试 only | `cli/main.py`，非主路径 |
| HR / 动机类 | — | 面试通用 |

---

## 一面（1–8）

### 1. RN 跨端页面接入 AI Coding 侧边栏，组件和状态怎么拆？

**Web 主战场映射：** ✅ 同一题，把 RN 侧边栏换成 **Web 工作台布局**

**复盘要点（按 CrossAgent Web 答）：**
- **布局**：主区（代码/Spec）+ 右侧 `ChatPage` 侧边栏
- **状态拆分**：`messages` / `isLoading` / `error` / `sseMeta`（`useAgentChat`）
- **与 Agent 解耦**：UI 只消费 SSE 事件（`text` | `tool_start` | `tool_end` | `done`），不 import Python

**对照项目：** `ChatPage.tsx`、`useAgentChat.ts`、`types/chat.ts`

---

### 2. AI 生成 RN 代码片段，前端如何做 diff 展示、确认、应用、回滚？

**CrossAgent 会碰到吗：** ✅ 会（implement / write_file 场景）

**复盘要点：**
- 先 `read_file` / `git_diff` 再改
- 工具返回结构化 JSON，UI 展示 diff
- 用户确认后再 `write_file`；回滚靠 git 或备份

**对照项目：** `fs.py`、`git_tools.py`；**缺**：确认门 UI、HITL middleware

---

### 3. 多模态输入（文本、图片、语音）前端交互流怎么设计？

**CrossAgent 会碰到吗：** ⚠️ 后期（当前 CLI 纯文本）

**复盘要点：**
- 输入类型 → 统一 Message 模型
- 图片：上传 / base64 / URL → 模型 multimodal API
- 语音：ASR → 文本再进 Agent

**对照项目：** 未做；千问是否支持 vision 需查 API

---

### 4. AI Agent 操作页面活动配置，权限和确认怎么处理？

**CrossAgent 会碰到吗：** ✅ 会（写文件、构建、git）

**复盘要点：**
- 读 vs 写分离；写/删/构建需确认
- 工具级权限（middleware）
- 审计日志

**对照项目：** `workspace.py` 路径沙箱；**缺**：权限 middleware、HITL、写前确认

---

### 5. RN 长列表里边生成边渲染，性能怎么控？

**CrossAgent 会碰到吗：** ✅ 会（Web 聊天流式 + 长 tool 结果）

**复盘要点：**
- 流式 token，不全量 append DOM
- 虚拟列表
- tool 结果 `shrink_tool_content` / 摘要后再进 context

**对照项目：** `services/context.py` trim；Web SSE 需控 chunk 频率

---

### 6. 给运营 Prompt 优化能力，前端如何降低误操作风险？

**CrossAgent 会碰到吗：** ✅ 会（Skill / system prompt 可编辑）

**复盘要点：**
- 草稿 / 预览 / 二次确认
- 版本对比、一键恢复
- 权限：谁改 prompt、谁只能读

**对照项目：** Skill 在 `skills/`；**缺**：Prompt 编辑 UI、版本管理

---

### 7. AI 返回 Markdown、链接、图片，前端如何安全渲染？

**CrossAgent 会碰到吗：** ✅ 会（聊天页展示 assistant 回复）

**复盘要点：**
- Markdown 白名单标签
- 链接 `rel="noopener"`、禁止 `javascript:`
- 图片域名白名单；XSS 过滤

**对照项目：** `apps/web` MessageList；需确认是否用 safe markdown 库

---

### 8. 怎么判断 AI Coding 是否真的提升了前端效率？

**CrossAgent 会碰到吗：** ✅ 会（产品 / Eval 方向）

**复盘要点：**
- 指标：任务完成率、人工修改行数、构建成功率、耗时
- Trace 回放 + 抽样评审
- A/B：有 Agent vs 无 Agent

**对照项目：** 架构文档有 Eval/Trace 规划；**未实现**

---

## 二面（1–8）

### 1. 设计小红书创新业务 AI Coding 工作台，从需求到上线怎么拆？

**CrossAgent 会碰到吗：** ✅ 整体产品架构题

**复盘要点：**
- 需求 → OpenSpec proposal → design → tasks → implement → archive
- 内核稳定（Tool loop）+ 可扩展（Skill / MCP）
- CLI → API → Web 渐进

**对照项目：** `docs/architecture.md`、`skills/crossagent-core`

---

### 2. 跨端 RN / Flutter / 小程序，AI 能力层怎么抽象？

**CrossAgent 会碰到吗：** ⚠️ 小程序侧对齐

**复盘要点：**
- Agent 层与端无关
- Tool 层感知 `detect_framework`、构建命令
- 端差异进 Skill / 文档 RAG，不进 core loop

**对照项目：** `project.py` detect_framework / run_build

---

### 3. Agent 自动改配置，如何防止线上活动被改坏？

**CrossAgent 会碰到吗：** ✅ 会

**复盘要点：**
- 沙箱工作区、禁止直写生产
- 变更必须 confirm + git diff
- 构建验证通过才 merge

**对照项目：** `CROSSAGENT_WORKSPACE`；**缺**：确认门、环境隔离

---

### 4. 模型生成动画配置，预览与降级怎么做？

**CrossAgent 会碰到吗：** ❌ 偏 RN 动画（小程序弱相关）

**复盘要点：** 预览 iframe / 沙箱渲染；失败 fallback 静态图或默认配置

---

### 5. RAG 检索组件库、业务文档、历史需求，前端如何展示引用来源？

**CrossAgent 会碰到吗：** ⚠️ 计划有

**复盘要点：**
- 消息里 citation 卡片（文件路径、段落、相似度）
- 点击跳转 spec / 组件 doc
- 与 tool 结果区分：RAG 是检索，tool 是执行

**对照项目：** 学习路线 Week2 RAG；**未实现**

---

### 6. AI 生成跨端代码 iOS 过 Android 不过，怎么定位？

**CrossAgent 会碰到吗：** ✅ 会（微信 vs 支付宝 vs H5）

**复盘要点：**
- 先确认编译目标与条件编译
- `run_build` 日志 + 平台字段对照
- 缩小 diff 范围

**对照项目：** prompt 里「先确认编译目标」；`run_build` tool

---

### 7. Prompt、模板、组件协议都在变，协作下版本怎么管？

**CrossAgent 会碰到吗：** ✅ 会

**复盘要点：**
- Skill / prompt 进 git
- OpenSpec change 目录版本化
- Tool schema 变更兼容旧 session

**对照项目：** Skill 文件、OpenSpec 规划；**缺**：prompt 版本号、迁移策略

---

### 8. AI 前端功能怎么做自动化测试？哪些不能 mock？

**CrossAgent 会碰到吗：** ✅ 会

**复盘要点：**
- 可测：tool schema、graph 路由、context trim、session 存取
- 集成：mock LLM 固定 tool_calls 序列
- 难 mock：真实模型 flaky → 录回放 / Eval 集

**对照项目：** 有 `test_tool_registry.py` 等；**缺**：graph 节点单测、LLM 集成测试

---

## 三面（1–6）

### 1. 小红书创新业务里，AI Coding 前端架构最核心的边界是什么？

**CrossAgent 会碰到吗：** ✅ 架构题

**建议答案骨架：**
- **内核**：Tool loop + 编排（稳定、可测）
- **扩展**：Skill（知）/ MCP（做）/ OpenSpec（流）
- **边界**：Agent 不直连 DB 细节；编排不实现 LLM；UI 不含业务 tool

**对照项目：** `senior-python-agent-architect` skill 分层

---

### 2. Agent + 跨端动态化，安全风险怎么控？

**CrossAgent 会碰到吗：** ✅ 会

**复盘要点：**
- 工作区沙箱、路径越界拒绝
- 危险 tool 黑名单（rm -rf、任意 shell）
- 敏感文件不 commit；MCP trust

**对照项目：** `workspace.py`；**缺**：权限 middleware、MCP trust 策略

---

### 3. AI 提速但线上问题变多，你怎么决策？

**CrossAgent 会碰到吗：** ✅ 开放题

**复盘要点：**
- 看失败类型：幻觉 vs 工具 vs 构建
- 加强 grounding（强制 tool）、HITL、Eval 门禁
- 不盲目扩 tool，先提高单次成功率

---

### 4. 多模态交互做成平台能力，先做哪些公共模块？

**CrossAgent 会碰到吗：** ⚠️ 中长期

**复盘要点：**
- 统一 Message / Attachment 模型
- 上传、转码、ASR 服务
- 模型路由（文本 vs 多模态）

---

### 5. 业务要炫交互，工程担心性能兼容，怎么推方案？

**CrossAgent 会碰到吗：** ✅ 协作题

**复盘要点：**
- MVP 先文本 + tool，流式其次
- 性能预算（首 token、列表帧率）
- 分阶段交付 + 可开关 feature flag

---

### 6. 除了生成速度，怎么定义 AI Coding 项目成功？

**CrossAgent 会碰到吗：** ✅ 产品题

**复盘要点：**
- 任务一次成功率、人工介入次数
- 构建/上线成功率
- 开发者主观满意度 + 留痕可追溯

---

## HR 面（1–6）

### 1. 为什么选小红书创新前端方向？

**准备：** 内容社区 + 活动创新 + AI 工程化交叉；个人经历挂钩

---

### 2. 跨端、AI、业务活动并行时怎么排优先级？

**准备：** P0 线上 / P1 核心链路 / P2 体验；时间盒；同步风险

---

### 3. 讲一次主动 push 技术落地的经历

**准备：** STAR；可讲 CrossAgent 从 0 搭 Tool loop / LangGraph

---

### 4. 入职后发现 AI Coding 效果不如预期怎么办？

**准备：** 先度量（哪类任务失败）→ 改 prompt/tool/Eval → 小步验证，不甩锅模型

---

### 5. 希望团队提供什么样的成长环境？

**准备：** 真实场景、代码评审、允许试错、业务与技术平衡

---

### 6. 内容社区里，技术创新和业务结果怎么看？

**准备：** 技术为业务指标服务；创新要有可验证假设和回滚

---

## CrossAgent 复盘清单（Web 为主 · 按优先级）

| 优先级 | 能力 | 面试题 | Web 现状 |
|--------|------|--------|----------|
| **P0** | **SSE 接真 Agent**（替换 mock route） | 一面 1、5 | `route.ts` 仍是 mock，未调 `run_turn` |
| **P0** | **FastAPI 流式桥接** | 一面 5 | 架构写了，Python API 层未建 |
| **P0** | Session 持久化（Web 会话） | 一面 4 | 前端 `messages` 仅内存，未接 SQLite |
| P1 | Tool 卡片 + 流式 coexist | 一面 5 | `ToolCard` 有，需测真 tool 链路 |
| P1 | Markdown 安全渲染 | 一面 7 | `MessageBubble` 待加固 |
| P1 | 写操作确认门（HITL UI） | 一面 2、4 | 未做 |
| P1 | Diff 预览 + 应用/回滚 UI | 一面 2 | 未做 |
| P2 | Trace / Eval | 一面 8 | 未做 |
| P2 | RAG 引用卡片 | 二面 5 | 未做 |
| P2 | Prompt / Skill 设置页 | 一面 6 | 未做 |
| P3 | 多模态（图/语音） | 一面 3 | 未做 |
| 低 | CLI 接 Session | — | 调试备用，非主路径 |

---

## 自测：用 CrossAgent Web 答一道综合题

**题：** 用户在 Web 侧边栏让 Agent 改小程序并构建，前后端怎么协作避免改坏？

**参考答案提纲（Web 为主）：**
1. **前端**：`useAgentChat.sendMessage` → SSE 收 `tool_start`/`tool_end`，Tool 卡片展示进度
2. **后端**：FastAPI 调 `ChatOrchestrator.run_turn`，ReAct 调 `detect_framework` → `read_file` → `git_diff`
3. **写前**：SSE 发 `confirm_required` 事件（待设计），Web 弹 diff 确认后再继续
4. **写后**：`tool_end` 带 `run_build` 结果，构建面板 / 终端展示日志
5. **持久化**：Session API 存 messages delta；Trace 可回放（待做）

---

## Web 链路现状（2025 复盘）

```text
✅ apps/web     ChatPage + useAgentChat + ToolCard + mock SSE
✅ services/    graph ReAct + tools(10) + run_turn
❌ 桥接        route.ts mock ≠ 真 Agent
❌ FastAPI     未建 api/ 层
❌ Session     Web 未接 SQLite
```

**下一步（Web 优先）：** FastAPI `POST /chat/stream` → 调 `run_turn` 并按 chunk 推 SSE → Next 代理或直连。

---

*最后更新：Web 为主路径；CLI 降为调试备用。*
