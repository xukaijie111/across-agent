# Customer Support Agent

来源：`open-source/500-AI-Agents-Projects-main/agents/13-customer-support-agent`

LangGraph-powered support agent with RAG knowledge base and automatic escalation routing.

**Framework**: LangGraph + FAISS  
**LLM**: GPT-4o-mini  

## Setup

```bash
pip install -r requirements.txt
# API Key 放在仓库根目录 .env（与 agent 目录同级上两级）
# 例：python-less/.env 内写 OPENAI_API_KEY=...
```

## Run

```bash
python agent.py

# Use your own .txt/.md knowledge base files
python agent.py --kb-dir docs/
```

## Features

- RAG over product knowledge base
- Automatic escalation detection for sensitive issues (billing disputes, data loss, etc.)
- Conversation history maintained
- Easily swap in your own knowledge base docs
