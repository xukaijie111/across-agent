# MCP 协议速查

## 三角色

| 角色 | 例子 | 职责 |
|------|------|------|
| **Host** | Claude Desktop、Cursor、你的 Agent 应用 | 承载 UI，管理多个 Client |
| **Client** | `ClientSession`、`MultiServerMCPClient` | 连一个 Server，发 JSON-RPC |
| **Server** | `calc_server.py`、`shop_server.py` | 提供 tools/resources/prompts |

本练习场里：**Client 脚本 = Client**，**servers/*.py = Server**。

## 分层

```
应用逻辑（你的 Python 脚本）
        ↓
MCP 协议（initialize, tools/list, tools/call, ...）
        ↓
JSON-RPC 2.0（method, params, id, result/error）
        ↓
传输（stdio 管道 / HTTP+SSE）
```

## 生命周期（stdio）

1. Client `spawn` Server 子进程（`command` + `args`）
2. Client → Server: `initialize`
3. Server → Client: capabilities
4. Client → Server: `notifications/initialized`
5. Client → Server: `tools/list`
6. Client → Server: `tools/call`（name + arguments）
7. Server → Client: `content` 数组（通常 `type: text`）

## tools/list 响应（概念）

```json
{
  "tools": [
    {
      "name": "add",
      "description": "Add two numbers.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "a": { "type": "integer" },
          "b": { "type": "integer" }
        },
        "required": ["a", "b"]
      }
    }
  ]
}
```

## tools/call

请求：`name` + `arguments`  
响应：`content: [{ "type": "text", "text": "..." }]`，`isError` 表示业务失败

## stdio vs HTTP

| | stdio | HTTP |
|---|-------|------|
| 配置 | `command`, `args`, `cwd?` | `url` |
| 谁启动 Server | Client spawn | Server 已运行 |
| 典型场景 | 本地工具、开发 | 远程微服务 |

## 和「商品/订单后端」的关系

```
LLM Agent
   → tools/call get_product
   → shop MCP Server（薄封装）
   → 原有 REST / 数据库
```

MCP 不是替代业务服务，是给 LLM 的标准工具接口。
