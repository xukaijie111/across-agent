# 今日吃透 MCP — 学习计划（纯 MCP，无 LangChain）

依赖只有 `pip install mcp`。代码在对话里要，自己手写。

---

## Step 0 · 准备（15min）

1. `pip install -r requirements.txt`
2. 读 `notes/protocol-cheatsheet.md`

---

## Step 1 · Inspector + 最小 Server（60min）

**目标**：肉眼看到 `initialize` / `tools/list` / `tools/call`

1. 手写 `servers/calc_server.py`（FastMCP：add、subtract）
2. `npx @modelcontextprotocol/inspector python servers/calc_server.py`
3. 记录 4 类 JSON 报文

**对话指令**：`给我 Step 1 calc_server 代码`

---

## Step 2 · 官方 SDK Client（60min）

**目标**：用 `ClientSession` + `stdio_client`，理解 Client 怎么 spawn Server

1. 手写 `clients/01_stdio_raw.py`
2. `--list-only` 列 tools
3. `--call add --args '{"a":3,"b":5}'`

**对话指令**：`给我 Step 2 raw client 代码`

---

## Step 3 · 商品/订单 Server（75min）

**目标**：MCP = 把后端能力暴露成 tools

1. 手写 `servers/shop_server.py`（get_product、list_orders、create_order）
2. Inspector + raw client 各测一遍

**对话指令**：`给我 Step 3 shop_server 代码`

---

## Step 4 · 多 Server（45min）

**目标**：一个 Client 脚本依次连接多个 MCP Server

1. 手写 `clients/02_multi_server.py`
2. 先连 calc list/call，再连 shop list/call

**对话指令**：`给我 Step 4 multi server 代码`

---

## Step 5 · 自己改 + 总结（45min）

- calc 加 `multiply`
- shop 加 `cancel_order`
- 写 `notes/my-summary.md`

**对话指令**：`Step 5 只给提示`

---

## Step 6 · 可选了解

- 读 `config/mcp.json.example`（Claude/Cursor 怎么配 Server，和代码无关）
- 中文资料：[mcp-guide-zh](https://github.com/mengxiangyu-meng/mcp-guide-zh)

---

## 验收

- [ ] Inspector 连 calc / shop 成功
- [ ] `01_stdio_raw.py` list + call 成功
- [ ] `02_multi_server.py` 两个 Server 都跑通
- [ ] 自己加过至少 1 个 tool
- [ ] 能解释 initialize → tools/list → tools/call 整条链
