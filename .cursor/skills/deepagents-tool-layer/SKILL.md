---
name: deepagents-tool-layer
description: >-
  Deep Agents 工具层架构参考（源码位于本机 open-source/deepagents-main）。
  说明 Middleware 注入工具、Backend 协议、MCP 加载、权限与 Skill 分离的设计，
  供 CrossAgent 设计 ToolRegistry / Provider 时对照。在用户讨论工具抽象、
  deepagents、LangChain middleware 或 MCP 集成时使用。
---

# Deep Agents 工具层架构参考

> 源码路径：`/Users/xukaijie/Desktop/open-source/deepagents-main`  
> 核心库：`libs/deepagents/deepagents/`  
> CLI 层：`libs/cli/deepagents_cli/`

CrossAgent 设计工具层时可对照本文，**不要照抄 LangChain 全家桶**，只借鉴分层思想。

---

## 1. 总览：不是「一个 tools.py」，而是 Middleware 栈

Deep Agents **不把工具写死在 agent 循环里**。入口是 `create_deep_agent()`（`graph.py`），底层用 LangChain 的 `create_agent(model, tools=..., middleware=...)`。

工具来源有三类，最终都在 **middleware 调用模型前** 合并进 `request.tools`：

| 来源 | 机制 | 典型工具 |
|------|------|----------|
| **用户传入** | `create_deep_agent(tools=[...])` | 自定义 `@tool`、MCP 转来的 `BaseTool` |
| **Middleware 注入** | 各 middleware 在 `wrap_model_call` 里追加 tools | `FilesystemMiddleware` → ls/read/write/grep… |
| **子 Agent** | `SubAgentMiddleware` | `task` 委派子 agent |

**默认内置**（README + `graph.py` docstring）：`write_todos`、文件系统工具、`execute`（需 sandbox backend）、`task`（子 agent）。

---

## 2. 核心文件地图

| 路径 | 职责 |
|------|------|
| `deepagents/graph.py` | 组装 middleware 栈，调用 `create_agent` |
| `deepagents/middleware/filesystem.py` | **文件系统工具**实现 + 注入 |
| `deepagents/middleware/permissions.py` | **权限**：`FilesystemPermission` + `_PermissionMiddleware` |
| `deepagents/middleware/_tool_exclusion.py` | 按名称过滤工具（provider profile） |
| `deepagents/middleware/skills.py` | **Skill 进 system prompt**，不是 action tool |
| `deepagents/backends/protocol.py` | **BackendProtocol**：存储/读写的抽象 |
| `deepagents/backends/filesystem.py` 等 | 具体 backend 实现 |
| `cli/deepagents_cli/mcp_tools.py` | **MCP 发现、加载、合并** |
| `cli/deepagents_cli/tools.py` | CLI 额外工具（如 `web_search`） |
| `cli/deepagents_cli/agent.py` | CLI 里 `create_deep_agent(..., tools=tools)` |

---

## 3. Middleware 栈顺序（决定谁能注入/过滤工具）

`create_deep_agent` 主 agent 栈（简化）：

```text
TodoListMiddleware
SkillsMiddleware          # 若传了 skills= 路径
FilesystemMiddleware      # 注入 ls/read_file/write_file/edit_file/glob/grep/execute
SubAgentMiddleware        # 注入 task
SummarizationMiddleware
PatchToolCallsMiddleware
[用户 middleware]
[profile extra_middleware]
_ToolExclusionMiddleware  # 按 excluded_tools 从 request.tools 删掉
AnthropicPromptCachingMiddleware
MemoryMiddleware          # 若传了 memory=
HumanInTheLoopMiddleware  # 若传了 interrupt_on=
_PermissionMiddleware     # 必须最后：wrap_tool_call 拦截执行
```

要点：

- **工具在 middleware 里「长出来」**，不是启动时一个静态 `TOOLS` 列表。
- **`_PermissionMiddleware` 必须最后**，才能看到所有 middleware 注入的工具，并在 **执行前/执行后** 拦截。
- **`_ToolExclusionMiddleware` 在靠后位置**，在模型看到 tools 之前做减法。

---

## 4. Backend 层：工具与存储解耦

`BackendProtocol`（`backends/protocol.py`）定义统一文件操作接口：`read`/`write`/`edit`/`ls`/`glob`/`grep` 等。

`FilesystemMiddleware` **不直接操作 OS**，而是调 `backend`：

- `StateBackend`：内存/会话态文件（默认）
- `FilesystemBackend`：真实磁盘 `root_dir`
- `CompositeBackend`：按路径前缀路由到不同 backend（CLI 里 `/large_tool_results/`、`/conversation_history/`）
- `SandboxBackend`：支持 `execute` 跑 shell

**对 CrossAgent 的启示**：工具实现应依赖 **`WorkspaceBackend` 接口**，而不是在 handler 里散落 `open()`/`subprocess`。

---

## 5. 权限怎么做（Deep Agents 版）

不是用户登录 RBAC，而是 **路径 + 操作类型规则**：

```python
FilesystemPermission(
    operations=["write"],  # read | write
    paths=["/**"],
    mode="deny",
)
```

- `read` 覆盖：`ls`, `read_file`, `glob`, `grep`
- `write` 覆盖：`write_file`, `edit_file`
- 规则 **按声明顺序，第一条匹配生效**；无匹配则 **默认 allow**
- `_PermissionMiddleware` 用 `wrap_tool_call`：执行前拒绝对路径；对 `ls`/`glob`/`grep` 结果 **事后过滤** 路径

还有 `interrupt_on={"edit_file": True}` → `HumanInTheLoopMiddleware`（执行前人工确认）。

**对 CrossAgent**：工具 risk（READ/MUTATE/DESTRUCTIVE）+ 路径 glob 规则 + HITL，与 deepagents 的 `FilesystemPermission` + `interrupt_on` 同构；用户登录 RBAC 应映射到「允许的最大 risk / 允许的 provider」。

---

## 6. MCP 怎么做（CLI 层，不在 core 库里硬编码）

`cli/deepagents_cli/mcp_tools.py`：

1. **发现配置**：用户级 + 项目级 `.mcp.json`（`discover_mcp_configs`）
2. **合并多份 config**（后加载覆盖先加载）
3. **项目 stdio MCP 要 trust**（`trust_project_mcp`、指纹存储）— 安全边界
4. **`langchain_mcp_adapters`**：`load_mcp_tools` / `MultiServerMCPClient.get_tools()` → `list[BaseTool]`
5. **与用户 tools 合并**后传入 `create_deep_agent(tools=...)`
6. **系统提示里追加 MCP 清单**（`local_context._build_mcp_context`），让模型知道有哪些 server/tool

MCP 工具在 Deep Agents 眼里 **与用户自定义 tool 一样**，都是 `BaseTool`；区别只在 **加载阶段** 和 **信任策略**。

**对 CrossAgent**：`McpProvider` 负责 3–4；`ToolRegistry` 负责与用户 builtin 合并；trust 策略可放在 `.crossagent/mcp.json` + CLI 确认。

---

## 7. Skill 与 Tool 如何分离（重要）

| | Skill | Tool |
|---|--------|------|
| **载体** | `SKILL.md`（YAML frontmatter + 说明） | `BaseTool` / middleware 注入的 callable |
| **加载** | `SkillsMiddleware` 从 **backend 路径** 读 skill 目录 | `FilesystemMiddleware` / 用户 tools / MCP |
| **给模型什么** | 写进 **system prompt**（渐进披露 metadata） | **tools schema**，模型发 `tool_calls` |
| **是否执行** | 不执行；指导模型何时读 `SKILL.md` 全文 | 执行并返回 `ToolMessage` |

Skill 支持多 source 叠加：**后加载覆盖同名 skill**（与 MCP config 合并策略类似）。

**对 CrossAgent**：坚持 `skills/crossagent-core/SKILL.md` 只做规范；行动走 Registry。**不要**把 OpenSpec 正文塞进 tool description。

---

## 8. Provider Profile：按模型裁剪工具

`profiles/_harness_profiles.py` 里 `_HarnessProfile` 支持：

- `tool_description_overrides`：按工具名改 description
- `excluded_tools`：`_ToolExclusionMiddleware` 从模型可见列表移除
- `extra_middleware`：按 provider 加中间件

即：**同一套 middleware 栈，不同模型可暴露不同工具子集**。

---

## 9. 与 CrossAgent 当前架构的对照

| Deep Agents | CrossAgent（目标） |
|-------------|-------------------|
| Middleware 注入 tools | `ToolProvider.list_tools()` |
| `create_agent` + `ToolNode` | 手写 `agent_loop` + 未来可换 LangGraph `ToolNode` |
| `BackendProtocol` | `WorkspaceBackend` / storage backend |
| `FilesystemPermission` | `ToolRisk` + `compile_tools(ctx)` |
| `mcp_tools.py` 加载 | `McpProvider` |
| `SkillsMiddleware` | `skill_loader` → system prompt |
| `interrupt_on` | OpenSpec confirm / approve 门 |
| 用户 `tools=[...]` | Registry 合并用户插件 |

CrossAgent **不必引入 LangChain Middleware**，但应复制其 **职责分离**：

```text
Provider（builtin / mcp）
    → Registry（合并、去重、compile、invoke）
    → Context（workspace、principal、stage、max_risk）
    → agent_loop（只调 Registry）
```

---

## 10. 建议阅读顺序（读 deepagents 源码）

1. `deepagents/graph.py` — `create_deep_agent` 全文，看清 middleware 顺序  
2. `middleware/filesystem.py` — 工具如何绑定 backend  
3. `middleware/permissions.py` — 执行拦截  
4. `middleware/_tool_exclusion.py` — 模型可见工具过滤  
5. `middleware/skills.py` 前 80 行 — Skill 与 backend 关系  
6. `cli/deepagents_cli/mcp_tools.py` — MCP 发现与 trust  
7. `cli/deepagents_cli/agent.py` — `create_deep_agent(..., tools=, backend=CompositeBackend(...))`

---

## 11. 一句话 takeaway

> **Deep Agents 的工具层 = Backend（存什么）+ Middleware（注入什么工具、何时过滤）+ 用户/MCP tools（扩展什么）+ Permission/HITL（允许什么）；Skill 只改 prompt，不进 tool 列表。**

CrossAgent 用更轻的 **ToolRegistry + Provider** 实现同样分层，避免绑死 LangChain，但分层思想可直接借鉴。
