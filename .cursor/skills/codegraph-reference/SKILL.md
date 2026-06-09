---
name: codegraph-reference
description: >-
  CodeGraph 本地代码知识图谱参考（源码位于本机 open-source/codegraph-main）。
  说明 tree-sitter 索引、SQLite 图、框架解析（含 Spring）、MCP 工具与
  codegraph_explore 用法，供 CrossAgent 设计 WorkspaceIndexer / 减少 list_dir
  时对照。在用户讨论 CodeGraph、工程索引、符号图、MCP 代码智能或
  workspace manifest 时使用。
---

# CodeGraph 代码知识图谱参考

> 源码路径：`/Users/xukaijie/Desktop/open-source/codegraph-main`  
> npm 包：`@colbymchenry/codegraph`  
> 项目数据：各仓库根目录 `.codegraph/`（SQLite）

CrossAgent 设计 **Workspace Knowledge Layer**（工程先索引、LLM 再查询）时优先对照本文，**不必自研完整 AST 图**时可评估直接集成 MCP 或借鉴 pipeline。

---

## 1. 定位：和 CrossAgent 缺口的对应关系

| CrossAgent 现状 | CodeGraph 做法 |
|-----------------|----------------|
| 裸 `list_dir` / `read_file` 勘探 | 启动时 `codegraph init` 建索引 |
| `grep_files` glob 易坏 | ripgrep + FTS5 + 符号图 |
| 不知 Maven 多模块结构 | `springResolver` 读 `pom.xml`、`@RestController` |
| prompt 里写 Maven 规则 | MCP `SERVER_INSTRUCTIONS` 教 Agent 用 `codegraph_explore` |

**mall 项目**：`projects/mall` 含 Java + TS，跑 `codegraph init` 后可索引 `server/` 与 `miniapp/src/`（`.wxml` 支持有限）。

---

## 2. 流水线（`CLAUDE.md`）

```text
files
  → ExtractionOrchestrator (tree-sitter WASM, 20+ 语言)
  → SQLite (nodes / edges / files, FTS5)
  → ReferenceResolver (import + frameworks/)
  → GraphTraverser (callers / callees / impact)
  → ContextBuilder → MCP 工具输出
```

**确定性解析**，非 LLM 摘要。

### 核心目录

| 路径 | 职责 |
|------|------|
| `src/index.ts` | `CodeGraph` 类：`init`/`indexAll`/`sync`/`searchNodes`/`buildContext` |
| `src/extraction/` | 按语言 extractors、`parse-worker.ts` |
| `src/resolution/frameworks/` | Spring、Gin、Express、Django、Rails… 路由 → handler 边 |
| `src/resolution/frameworks/java.ts` | **Spring Boot**：检测 `pom.xml`/`build.gradle`，`@RestController` 等 |
| `src/graph/` | 图遍历、影响半径 |
| `src/context/` | 给 Agent 的 markdown/JSON 上下文 |
| `src/mcp/tools.ts` | MCP 工具实现（`codegraph_explore` 等） |
| `src/mcp/server-instructions.ts` | MCP initialize 注入的系统级 playbook |
| `src/sync/` | 文件监听 + debounce 增量 sync |

---

## 3. CLI 与索引生命周期

```bash
cd your-project
codegraph init          # 创建 .codegraph/ 并默认全量索引
codegraph sync          # 手动增量（平时 watcher 自动 sync）
codegraph status        # 索引状态、pending 文件
codegraph install       # 写入 Cursor/Claude Code 等 MCP 配置
```

- 索引存本地 SQLite，**数据不出机器**
- 文件变更：FSEvents/inotify → debounce（默认 ~2s）→ 自动 re-index
- stale 文件：MCP 响应带 `⚠️` banner，提示 Agent 对该文件用 Read

---

## 4. MCP 工具（Agent 消费层）

| 工具 | 用途 |
|------|------|
| **`codegraph_explore`** | **主工具**：自然语言或符号名 → 相关源码 + 调用关系（常 1 次够用） |
| `codegraph_search` | 按符号名定位（无源码） |
| `codegraph_node` | 单符号：当前磁盘源码 + caller/callee（可替代 Read） |
| `codegraph_callers` / `codegraph_callees` | 调用链 |
| `codegraph_impact` | 改动影响面 |
| `codegraph_files` | 目录/文件列表 |
| `codegraph_status` | 索引是否就绪 |

`getExploreBudget(fileCount)` / `ExploreOutputBudget`：按项目规模自适应输出上限，避免小仓库 context 膨胀。

**反模式**（写在 `server-instructions.ts`）：不要 grep+read 循环替代 explore；不要对可命名符号直接 Read。

---

## 5. 与 Chatbox / Deep Agents 的边界

| | CodeGraph | Chatbox KB | Deep Agents Memory |
|--|-----------|------------|-------------------|
| 对象 | **代码库** AST 图 | 用户上传文档 RAG | 人工 `AGENTS.md` |
| 构建 | 自动 `init` | 上传后 chunk+embed | 启动读 markdown |
| 查询 | 符号/调用/路由 | 语义 chunk | 全文在 prompt |

---

## 6. CrossAgent 集成思路

**A. 外挂 MCP（最快）**  
`CROSSAGENT_WORKSPACE=projects/mall` 下先 `codegraph init`，CrossAgent 增加 MCP client 暴露 `codegraph_*` 工具。

**B. 内嵌轻量版**  
只借鉴：启动解析 `pom.xml`/`package.json` + rg 扫 `@RestController` → `manifest.json` 注入 system prompt（Phase 1）。

**C. 深集成**  
子进程调 CodeGraph CLI 或只读 `.codegraph/codegraph.db`。

---

## 7. 建议阅读顺序

1. `README.md` — 基准与 `codegraph init` 流程  
2. `CLAUDE.md` — 模块地图与 build/test  
3. `src/mcp/server-instructions.ts` — Agent 行为约束  
4. `src/mcp/tools.ts` — `codegraph_explore` 实现与输出预算  
5. `src/resolution/frameworks/java.ts` — Spring/Maven 多模块相关  

---

## 8. 一句话

> **CodeGraph = 本地 SQLite 代码知识图 + MCP；工程理解在索引阶段完成，Agent 用 `codegraph_explore` 查询，而不是每层 `list_dir`。**
