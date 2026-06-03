# MCP 学习练习场

独立于 CrossAgent，**纯 MCP**（官方 Python SDK + Inspector），不涉及 LangChain。

目录和空文件已建好，代码在对话里按步骤给出，你自己手写。

## 环境

直接用 **base** 环境：

```bash
cd mcp-learn
pip install -r requirements.txt
node -v   # Inspector 需要
```

## 目录结构

```
mcp-learn/
├── README.md
├── LEARNING_PLAN.md
├── requirements.txt
├── notes/
│   ├── protocol-cheatsheet.md
│   └── my-summary.md
├── servers/
│   ├── calc_server.py           # Step 1
│   └── shop_server.py           # Step 3
├── clients/
│   ├── 01_stdio_raw.py          # Step 2  官方 SDK Client
│   └── 02_multi_server.py       # Step 4  连多个 Server
└── config/
    └── mcp.json.example         # 可选：了解 Host 怎么配 Server
```

## 学习路径

| Step | 内容 |
|------|------|
| 1 | `calc_server.py` + Inspector |
| 2 | `01_stdio_raw.py` 官方 Client |
| 3 | `shop_server.py` 商品/订单 |
| 4 | `02_multi_server.py` 依次连 calc + shop |
| 5 | 自己加 tool + 写总结 |

## 开始

1. 读 `LEARNING_PLAN.md`
2. 对话里说：`给我 Step 1 calc_server 代码`
