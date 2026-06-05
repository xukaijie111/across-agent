# 聊天协议与消息组装

本文说明 CrossAgent **当前实现**中：checkpoint 存什么、后端如何返回、前端如何组装 `messageList`。  
代码参考：

| 区域 | 路径 |
|------|------|
| 后端 API（TS，默认 `make api`） | `apps/server/src/index.ts` |
| SSE 事件定义 | `apps/server/src/graph/chatEvents.ts` |
| 流式与历史 | `apps/server/src/graph/streamRunner.ts` |
| Checkpoint | `apps/server/src/checkpoint.ts`、`apps/server/src/graph/state.ts` |
| 前端协议 | `apps/web/src/lib/chat-protocol.ts` |
| 前端 SSE | `apps/web/src/lib/sse.ts` |
| 前端 Hook | `apps/web/src/hooks/useAgentChat.ts` |
| Python 后端（`make api-py`，逻辑对齐） | `api/main.py`、`services/graph/stream_runner.py` |

---

## 一、三层数据（不要混为一谈）

同一次对话在系统里有 **三种形状**，来源与用途不同：

```
┌─────────────────────────────────────────────────────────────┐
│  ① Checkpoint（SqliteSaver，thread_id = session_id）          │
│     LangGraph AgentState.messages[]                          │
│     给 LLM 续写用：system / user / assistant / tool          │
└───────────────────────────┬─────────────────────────────────┘
                            │
          ┌─────────────────┴─────────────────┐
          ▼                                   ▼
┌──────────────────────┐          ┌──────────────────────┐
│  ② 实时 SSE           │          │  ③ 历史 API           │
│  ChatEvent 事件流     │          │  getUiMessages()      │
│  来自 graph stream    │          │  来自 getState()      │
└──────────┬───────────┘          └──────────┬───────────┘
           │                                  │
           └──────────────┬───────────────────┘
                          ▼
              ┌──────────────────────┐
              │  前端 messageList     │
              │  ChatMessage[]        │
              │  给人看的 UI 状态     │
              └──────────────────────┘
```

**结论：**

- Checkpoint **不是**直接返回给前端的格式。
- 实时 SSE 与历史 API 是 **两条不同的「投影」**，规则尚未统一。
- 前端 `ChatMessage` 是 **第四种** UI 模型，由前端 reducer 或历史映射得到。

---

## 二、Checkpoint 里存什么

### 2.1 State 与 reducer

`AgentState.messages` 使用 **concat reducer**：每个 graph node 返回的 patch 会 **追加** 到数组末尾。

```typescript
// apps/server/src/graph/state.ts
messages: Annotation<ChatMessage[]>({
  reducer: (left, right) => left.concat(right),
})
```

### 2.2 单条 message 的形态（OpenAI / LangGraph 风格）

类型为 `Record<string, unknown>`（见 `apps/server/src/context.ts`），常见字段：

| role | 含义 | 典型字段 |
|------|------|----------|
| `system` | 系统提示 | `content` |
| `user` | 用户输入 | `content` |
| `assistant` | 模型输出 | `content`，可能有 `tool_calls` |
| `tool` | 工具执行结果 | `tool_call_id`，`content`（常为 JSON 字符串） |

### 2.3 一轮用户提问在 checkpoint 里往往是多条

用户只发一句，agent 跑 ReAct 后 checkpoint 可能类似：

```
user:      "读 package.json"
assistant: { content: "我先看下", tool_calls: [read_file] }
tool:      { tool_call_id: "...", content: "{...}" }
assistant: { content: "已经读完了…" }   // 无 tool_calls
```

这是 **模型上下文**，不是 UI 里「一个气泡」。

---

## 三、后端 API 概览

| 方法 | 路径 | 作用 |
|------|------|------|
| `POST` | `/session/create` | 创建会话，返回 `{ session_id }` |
| `POST` | `/chat/stream` | 流式对话，SSE |
| `POST` | `/session/histroy` | 加载历史（路径拼写暂保留 typo） |
| `GET` | `/ok` | 健康检查 |

请求体（流式）：

```json
{ "session_id": "...", "message": "用户输入" }
```

前端 **不再上传历史**；后端从 checkpoint 读取已有 messages，只追加本轮 user input。

---

## 四、实时 SSE：后端发什么

### 4.1 传输格式

每个 SSE 帧（`apps/server/src/index.ts`）：

```
id: evt-1
event: chat
data: {"type":"tool_start",...}

```

`data` 为 JSON，类型为 `ChatEvent`（见 `chatEvents.ts`）。

### 4.2 事件类型

| type | 字段 | 含义 |
|------|------|------|
| `tool_start` | `id`, `name`, `args` | 开始调用工具 |
| `tool_end` | `id`, `result?`, `error?` | 工具结束 |
| `text` | `delta` | 助手正文 **token 流**（OpenAI `stream: true`，每个 delta 一条事件） |
| `done` | — | 本轮结束 |
| `error` | `message` | 异常 |

`format`：`plain` | `markdown`（助手默认 `markdown`）。**讨论结论：可按 role 推断，后续可删除该字段。**

### 4.3 单轮典型顺序

```
tool_start → tool_end → (可能多轮 tool) → text → done
```

### 4.4 事件从哪来（StreamRunner）

`runTurn(sessionId, input, onEvent)` 监听 LangGraph `stream_mode: "updates"`，用回调推送事件（无 `yield`），**不是**每步 `getState()` 再转换：

```
agent 节点更新:
  若 last 有 tool_calls → yield tool_start（每个 tool 一条）
  否则 → 记下 finalAssistant（最后一条无 tool 的 assistant）

tools 节点更新:
  每个 tool message → yield tool_end

图跑完后:
  若 finalAssistant 有 content → yield text（仅一次）
  yield done
```

**当前局限（实现层面）：**

- 带 `tool_calls` 的 assistant 若同时有 `content`，**不会** yield `text`。
- 只有 **最后一条** 无 `tool_calls` 的 assistant 正文会通过 `text` 发出。
- 中间多段 assistant 文字在 SSE 里 **可能丢失**。

---

## 五、历史 API：后端发什么

### 5.1 调用

```
POST /session/histroy?session_id=<uuid>
```

### 5.2 处理流程

```
getState(sessionId).values.messages
  → getUiMessages()  // streamRunner 内联过滤
  → JSON 数组
```

### 5.3 返回形状（HistoryMessage）

```json
[
  { "role": "user", "content": "...", "format": "plain" },
  { "role": "assistant", "content": "...", "format": "markdown" }
]
```

### 5.4 getUiMessages 当前规则

- 保留所有 `role === "user"`。
- 仅保留 **没有 `tool_calls`** 且 `content` 非空的 `assistant`。
- **跳过** `system`、`tool`、以及带 `tool_calls` 的 assistant。

**当前局限：**

- 无 `tools` 字段，刷新后 ToolCard 消失。
- 一轮里多条 assistant 正文会被拆成 **多条** UI assistant（若都有 content 且无 tool_calls），与流式「合并成一条」不一致。
- 与 SSE 使用 **不同代码路径**，规则不对齐。

---

## 六、前端 UI 模型：ChatTurn（按轮）

定义见 `apps/web/src/lib/chat-protocol.ts`。

```typescript
type MessagePart =
  | { type: "text"; content: string }
  | { type: "tool"; id; name; args; status; result?; error? };

interface ChatTurn {
  id: string;
  user: { content: string };
  assistant: { contents: MessagePart[] };  // 按 SSE 到达顺序 append
}
```

### 6.1 turns 与 messageList

- **`turns: ChatTurn[]`** = 整个会话（`useAgentChat`）
- **每一项** = 一轮：用户问 + 助手答
- **不是**每个 SSE 事件一项；流式只改 **`turns[last].assistant.contents`**

### 6.2 渲染

`MessageList` → `TurnBubble`：

- `user.content` → 用户气泡（plain）
- `assistant.contents.map(...)` → text（markdown）/ tool（ToolCard），**不调序**

---

## 七、前端如何组装 turns

### 7.1 状态拆分（流式优化）

| 状态 | 含义 |
|------|------|
| `completedTurns` | 已结束轮次，`React.memo(TurnBubble)`，高频 text 不重绘 |
| `streamingTurn` | 当前轮，仅此处接收 text delta / tool 事件 |
| `done` | `streamingTurn` 并入 `completedTurns` 并清空 |

### 7.2 两条入口

| 场景 | 入口 | 行为 |
|------|------|------|
| 进页 / 刷新 | `historyToTurns` | `setCompletedTurns`，`streamingTurn = null` |
| 发送消息 | `setStreamingTurn(createTurn(text))` | SSE → `applyChatEventToTurn` |

### 7.3 发送消息流程

```
1. setStreamingTurn(createTurn(text))
2. POST /chat/stream
3. text/tool 事件 → applyChatEventToTurn(streamingTurn)
4. done → completedTurns.push(streamingTurn); streamingTurn = null
```

### 7.4 applyChatEventToTurn 规则

| 事件 | 操作 |
|------|------|
| `tool_start` | `assistant.contents` **push** tool |
| `tool_end` | 按 `id` **更新** contents 里对应 tool |
| `text` | 拼接或 **push** text part（每个 delta 触发一次） |
| `done` / `error` | 在 hook 层处理，不改 turn 内容 |

### 7.4 历史加载

`historyToTurns`：把 API 扁平 `[user, assistant, user, …]` **两两合并** 为 `ChatTurn`（assistant 仅 text part，暂无 tools）。

---

## 八、端到端对照（一轮对话）

```
用户: "读 package.json"

── Checkpoint（跑完后）──
user → assistant(tool_calls) → tool → assistant(content)

── SSE（流式）──
tool_start → tool_end → text(delta)* → done
（text 为 LLM token 流，非整段一块）

── 前端 turns（流式结束后）──
[ { user: { content: "..." }, assistant: { contents: [tool, tool, text] } } ]

── 历史 API（刷新后）──
[ { role: user, ... }, { role: assistant, content: "..." } ]   // 无 tools
```

---

## 九、已知问题与改进方向（讨论结论）

### 9.1 问题汇总

| 问题 | 原因 |
|------|------|
| 实时与历史形状不一致 | SSE 走 stream updates；历史走 getUiMessages，两套规则 |
| 刷新后 ToolCard 丢失 | 历史 API 不返回 tools |
| 中间 assistant 文字可能丢失 | 已改 LLM stream；带 tool 的 preamble 视模型而定 |
| 气泡内顺序 | 已改 `contents.map` 按事件顺序 |
| Checkpoint 不能直接给前端 | 模型格式（多段 assistant/tool）≠ UI 格式（一轮一条） |

### 9.2 建议：公共转换函数 `toUiMessages`

从 checkpoint `messages[]` 统一映射为前端 `ChatMessage[]`（或带 `tools` 的等价结构）：

```
输入: checkpoint messages[]
输出: UiMessage[]  // user 一条 + assistant 一条（含 tools + 有序正文）

用法:
  历史: getState() → toUiMessages(all) → 返回前端
  实时: 每个 node 后 getState() → toUiMessages(all) → 取最后一轮 assistant 推送
```

目标：**历史与实时共用同一转换**，checkpoint 仍为唯一真相，UI 为投影。

### 9.3 format 字段

助手固定 markdown、用户固定 plain 即可，**format 字段可省略**，由 `role` 推断。

---

## 十、与 Chatbox 的差异（简要）

| | CrossAgent（当前） | Chatbox |
|---|-------------------|---------|
| UI 列表 | `messages[]` | `session.messages[]` |
| 单条 assistant 内部 | `content` + `tools[]` | `contentParts[]`（有序） |
| 持久化 | 服务端 checkpoint | 本地 storage 存 UI Message |
| 流式组装 | 前端 `applyChatEvent` | 前端 `processStreamChunk` |

CrossAgent 不必须上 `contentParts`；但若需 tool 与正文 **严格按时间穿插**，或增加 reasoning / 图片等类型，有序 `parts[]` 会更合适。

---

## 十一、相关命令

```bash
make api      # TS 后端 :8000
make api-py   # Python 后端 :8000（协议对齐）
```

前端环境变量：`apps/web/.env.local` → `NEXT_PUBLIC_API_BASE=http://localhost:8000`
