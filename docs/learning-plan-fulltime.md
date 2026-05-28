# Agent 全栈 · 全职学习规划（CLI 优先版 · 3 周）

> **状态**：已离职，全职投入  
> **策略**：**先 CLI 打通 Agent 全链路，前端放到第 3 周可选**  
> **起点**：① Tool Calling 已跑通  
> **目标**：2.5 周 CLI 可演示闭环 + 0.5～1 周包装投递  

---

## 总览

| 周 | 主题 | 里程碑（全部 CLI 可验收） |
|----|------|---------------------------|
| **第 1 周** | CLI 对话 + Context + LangGraph + OpenSpec | `cross-agent chat` / `change propose` 能跑 |
| **第 2 周** | 构建日志 + RAG + MCP + implement + Trace | 终端里能看构建、文档检索、轨迹回放 |
| **第 3 周** | Eval + Docker + 录屏 + 文章 + 投递 | 批跑 Eval、README、终端 Demo 录屏 |
| **可选** | Next.js UI | 有 offer 面试前再补，不作为阻塞项 |

**面试演示**：终端录屏 + 架构图 + 文章，足够应对 **Agent 应用 / 后端 Agent** 向岗位。

---

## 每日节奏（CLI 版）

| 时段 | 做什么 |
|------|--------|
| 上午 3～4h | 后端 Agent / 编排 / RAG |
| 下午 3～4h | CLI 命令 + 联调 + 写 eval case |
| 晚上 1h | 复盘、面试题、更新 README |

**原则**：每个能力都对应一条 **CLI 子命令**，不依赖浏览器。

---

## CLI 命令规划（目标形态）

```bash
# 对话（Tool Calling）
python -m cli chat "检测 ./ 并编译微信"
python -m cli chat -i                    # 交互 REPL

# OpenSpec 变更流
python -m cli change new "分享卡片"
python -m cli change propose <id>
python -m cli change confirm <id>        # 确认需求
python -m cli change design <id>
python -m cli change approve <id>        # 批准方案
python -m cli change implement <id>      # 实施 + 构建

# 可观测
python -m cli trace show <trace_id>
python -m cli eval run
python -m cli spec list                  # 列出 openspec/ 产物
```

技术栈：`typer` + `rich`（表格/面板/进度条）+ 现有 `services/`。

---

## 第 1 周：Agent 核心（无前端）

### Day 1 — CLI 对话 + ① 收尾

- [x] `chat_with_tools` 循环
- [ ] 修稳 `_assemble_messages`（`model_dump()`）
- [ ] `cli/chat.py`：`chat` 子命令，调 `chat_with_tools`
- [ ] `rich` 打印：🔧 工具名、参数、返回摘要
- [ ] 交互模式：`chat -i` 多轮（messages 累积）

**验收**

```bash
python -m cli chat "检测 ./ 并编译微信"
# 终端看到 tool 调用 + 最终中文总结
```

**可选（不阻塞）**：FastAPI `POST /chat` 以后再加。

---

### Day 2 — ② Context 工程

- [ ] `services/context.py`：组装、裁剪、token 估算
- [ ] `cli chat` 加 `--verbose` 打印 Context 组成（system/history/tool 各占多少）
- [ ] 长 tool 结果自动摘要再塞回 messages

**验收**：`chat -v` 能看到 token 拆分；能口述裁剪策略。

---

### Day 3 — LangGraph 入门 + OpenSpec 目录

- [ ] `openspec/specs/`、`openspec/changes/<name>/`
- [ ] `services/openspec_io.py`
- [ ] `orchestration/graph.py`：`propose → END`（先单节点）

**验收**：`change propose` 生成 `proposal.md`。

---

### Day 4 — 五阶段图 + 确认门（CLI）

- [ ] Graph：`propose → confirm → design → approve → implement`
- [ ] `status.yaml` 或 LangGraph interrupt
- [ ] `change confirm` / `change approve` 在终端 y/n 确认

**验收**：不 confirm 不进 design（CLI 里可验证）。

---

### Day 5 — design + tasks

- [ ] 节点生成 `design.md`、delta `specs/`、`tasks.md`
- [ ] `cli spec cat <change_id> proposal|design|tasks`

**验收**：走完 propose → confirm → design → approve。

---

### Day 6 — implement 接 Tool Loop

- [ ] `implement` 节点：读 tasks.md，调 `chat_with_tools` 或逐步 execute_tool
- [ ] 终端打印每步 task `[x]`
- [ ] `run_build` 分阶段日志（mock 即可）

**验收**：`change implement <id>` 跑完 tasks 并构建。

---

### Day 7 — 第 1 周复盘

- [ ] README + Mermaid 架构图
- [ ] 10 条面试笔记（Tool / Context / 编排）
- [ ] 终端录屏 1 分钟：chat + change 流程

**周末交付**：CLI 完成 **对话 + OpenSpec 五阶段**。

---

## 第 2 周：构建 / RAG / MCP / Trace

### Day 8 — 构建日志（终端版，不用 SSE 前端）

- [ ] `services/build.py` 异步 yield logs
- [ ] `rich.live` 或逐行 print 阶段：detect → install → compile → artifact
- [ ] implement 时自动触发

**验收**：终端实时刷构建日志（无需 Web）。

---

### Day 9 — ④ RAG

- [ ] Taro/uni-app 文档 Markdown
- [ ] `services/rag.py` + Chroma/pgvector
- [ ] `cli chat` 检索后显示「引用来源」

**验收**：问 API 问题，CLI 打印引用片段路径。

---

### Day 10 — ⑤ MCP

- [ ] MCP Server 暴露 detect / build
- [ ] Agent 改走 MCP 调用
- [ ] `cli tools list` 列出已注册工具

---

### Day 11 — Trace

- [ ] 每步写入 `logs/traces/<id>.jsonl`
- [ ] `cli trace show <id>`：rich 表格展示 Thought/Tool/Result

**验收**：一次完整 change 可查 trace。

---

### Day 12 — Docker（仅 agent，无 web）

- [ ] `docker-compose`：agent + postgres（向量库，可选）
- [ ] 构建沙箱（可选真 npm build）

---

### Day 13～14 — 联调 + 修 bug

- [ ] 端到端：`change new` → … → `implement` → `trace show`
- [ ] 更新 `docs/architecture.md`

**第 2 周末交付**：CLI 全链路 + RAG + MCP + Trace。

---

## 第 3 周：Eval + 包装 + 投递

### Day 15～16 — Eval

- [ ] `eval/cases.json` 20 条
- [ ] `cli eval run` → 输出 pass rate 表格（rich）
- [ ] 改 prompt 前后对比，结果写 `logs/eval/`

---

### Day 17 — 作品包装

- [ ] README：安装、命令一览、架构图、GIF/录屏链接
- [ ] 技术文 1 篇（CLI Agent + OpenSpec + LangGraph）
- [ ] 终端录屏 2～3 分钟（asciinema 或 OBS）

---

### Day 18～19 — 简历 + 面试稿

- [ ] 简历项目段（见下，去掉「必须 Next.js」）
- [ ] 20 道面试题自答
- [ ] 开始投递

---

### Day 20～21 — 投递 + 可选前端

| 优先级 | 任务 |
|--------|------|
| P0 | 每天投递 + 复盘 JD |
| P1 | 修 Eval 失败 case |
| P2 | **可选**：最简 Next.js 只包一层聊天（1～2 天，有面试再补） |

---

## 前端何时做？

| 场景 | 建议 |
|------|------|
| 投 **Agent 应用 / 后端 / 全栈（偏工程）** | CLI + 录屏 **够** |
| 投 **偏前端全栈 Agent** | 第 3 周末或拿面试后补 2 天聊天 UI |
| 你有前端长板 | UI 反而是 **加分项**，不是第一周必做 |

---

## 简历描述（CLI 版）

```
CrossAgent CLI - 多端小程序 Agent 研发工具
- OpenSpec + LangGraph：proposal → 确认 → design → 批准 → implement
- 手写千问 Tool Calling；MCP 工具链；RAG（Taro/uni-app 文档库）
- 终端构建流水线、Trace 回放、20 条 Eval 批跑与 pass rate
- Python / Typer / LangGraph / pgvector / Docker Compose
- 录屏 Demo + 技术文章：[链接]
```

---

## 进度打卡

```
[x] ① Tool Calling
[ ] Day1  CLI chat + rich 输出
[ ] Day2  Context
[ ] Day3-6  OpenSpec + LangGraph（CLI 确认门）
[ ] Day8-11  构建 / RAG / MCP / Trace（CLI）
[ ] Day15+  Eval + 录屏 + 投递
[ ] 可选   Next.js UI
```

---

## 相关文档

- [learning-plan.md](./learning-plan.md) — 知识点清单  
- [architecture.md](./architecture.md) — 架构分层  
- [qwen-setup.md](./qwen-setup.md) — 千问接入  
