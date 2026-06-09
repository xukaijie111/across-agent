# Subagents

各业务 Agent 独立目录，由 `server/runners/` 桥接到通用 API。

| 目录 | 说明 |
|------|------|
| `customer_support/` | 服装客服（LangGraph + RAG + 退货确认 interrupt） |
| `chat_assistant/` | 日常聊天助手（不联网，不确定不编造；Runner id: `echo`） |

新增 Agent：复制目录模板 → 实现 `agent.py` → 在 `server/runners/` 注册 Runner。
