# Subagents

各业务 Agent 独立目录，由 `server/runners/` 桥接到通用 API。

| 目录 | 说明 |
|------|------|
| `customer_support/` | 服装客服（LangGraph + RAG + 退货确认 interrupt） |
| `chat_assistant/` | 日常聊天助手（不联网，不确定不编造；Runner id: `echo`） |
| `sql_query/` | 自然语言查 MySQL demo 电商库（Runner id: `sql-query`） |
| `meeting_notes/` | 会议文字稿 → Markdown 纪要（Runner id: `meeting-notes`） |
| `persona/` | 个人分身 RAG（简历 + Agent 知识库，Runner id: `persona`） |

新增 Agent：复制目录模板 → 实现 `agent.py` → 在 `server/runners/` 注册 Runner。
