---
name: 500-ai-agents-reference
description: >-
  500+ AI Agent Projects 本地参考源码（位于 open-source/500-AI-Agents-Projects-main）。
  说明 agents/ 下 20 个可运行 demo 的索引、框架分布与选型建议，供独立应用形态 Agent
  开发时对照。在用户讨论应用 Agent、客服/RAG/SQL 问数/研报、500-AI-Agents-Projects
  或要从参考 demo  fork 新 agent 时使用。
---

# 500+ AI Agent Projects 参考源码

> **源码路径**：`/Users/xukaijie/Desktop/open-source/500-AI-Agents-Projects-main`  
> **可运行 demo**：`agents/`（20 个，各自独立 `requirements.txt` + `.env.example`）  
> **索引用途**：根目录 `README.md`（500+ 外链用例表，偏浏览）

做**独立应用 Agent**（非 IDE 写代码）时，优先读 `agents/` 里的实现，不要从根目录大表猜架构。

---

## 1. 快速启动任意 demo

```bash
cd /Users/xukaijie/Desktop/open-source/500-AI-Agents-Projects-main/agents/<agent-name>
pip install -r requirements.txt
cp .env.example .env   # 填 OPENAI_API_KEY 等
python agent.py
```

完整索引：`agents/README.md`。

---

## 2. Demo 索引（按产品形态）

| # | 目录 | 框架 | 形态 | 难度 |
|---|------|------|------|------|
| 01 | `01-web-research-agent` | LangGraph + Tavily | 搜索 → 结构化报告 | ⭐⭐ |
| 03 | `03-pdf-qa-agent` | LlamaIndex | 文档 RAG + 多轮问答 | ⭐⭐ |
| 04 | `04-sql-query-agent` | LangChain | 自然语言查库（含电商 demo 库） | ⭐⭐ |
| 08 | `08-data-analysis-agent` | LangChain + pandas | CSV/Excel 分析 | ⭐⭐ |
| 10 | `10-meeting-notes-agent` | LangChain | transcript → JSON 纪要 | ⭐ |
| 11 | `11-stock-research-agent` | LangChain + yfinance | 拉数据 + 分析 | ⭐⭐ |
| 13 | `13-customer-support-agent` | LangGraph + FAISS | RAG 客服 + 升级规则 | ⭐⭐⭐ |
| 19 | `19-competitive-analysis-agent` | LangGraph | 竞品多步流水线 → 报告 | ⭐⭐⭐ |
| 05/12/14/18 | CrewAI 系列 | CrewAI | 多角色内容生成（邮件/旅行/社媒/求职） | ⭐–⭐⭐ |

**写代码向（通常跳过）**：`02-code-review-agent`、`07-github-issue-triager`、`15-unit-test-generator`、`16-documentation-writer`。

---

## 3. 选型速查

| 目标 | 首选 demo | 关键文件 |
|------|-----------|----------|
| 对话 + 知识库客服 | 13 | `agent.py`：`retrieve → check_escalation → generate` |
| 问业务数据 | 04 | `agent.py`：`create_sql_agent` + demo SQLite 电商表 |
| 上传文档问答 | 03 | `agent.py`：LlamaIndex `VectorStoreIndex` + chat engine |
| 运营/行业研报 | 01 或 19 | 01：Tavily 搜索；19：固定三步 LangGraph |
| 一次性结构化输出 | 10 | 单 LLM + JSON schema |

---

## 4. 目录约定（每个 demo）

```
agents/NN-name/
  agent.py           # 入口
  requirements.txt
  .env.example
  README.md
  metadata.yaml      # title / framework / tags / industry
```

Fork 到新项目：复制整个文件夹，改 `metadata.yaml` 与知识库/数据源即可。

---

## 5. 建议阅读顺序

1. `agents/README.md` — 20 个 demo 总表  
2. 按场景选一个 `agent.py` 通读（通常 <200 行）  
3. 根目录 `README.md` — 仅当需要按行业/框架浏览更多外链案例时  

---

## 6. 一句话

> **本地参考库 = `open-source/500-AI-Agents-Projects-main/agents/`；每个文件夹是一个可跑的应用 Agent 样板，先 copy 再改，不要从零猜架构。**
