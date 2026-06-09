# python-less

独立 Agent 实验工作区。

## 目录结构

```
server/
  main.py                   # 通用 API（FastAPI + SSE）
  runners/                  # Agent 适配器
  subagents/                # 各子 Agent 实现
    customer-support-agent/
web-h5/                     # 手机 H5 调试台（Vue3 + Vant）
scripts/
  start-agents.sh           # 一键启动
```

## 快速启动

### 1. 依赖

```bash
pip install -r server/requirements.txt
cd web-h5 && npm install
```

根目录 `.env` 配置 `OPENAI_API_KEY`（客服与聊天助手均需要）。

### 2. 启动

```bash
./scripts/start-agents.sh --install   # 首次
./scripts/start-agents.sh
```

手机浏览器访问：`http://<你的电脑IP>:5173`

### 单独启动

```bash
make agent-dev
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/agents` | Agent 列表 |
| POST | `/api/sessions` | 创建会话 |
| POST | `/api/chat/stream` | SSE 聊天 |
| POST | `/api/chat/resume` | SSE 恢复中断 |
| POST | `/api/sessions/{id}/reset` | 清空会话 |

## 新增 Agent

1. 在 `server/subagents/<your-agent>/` 实现逻辑  
2. 在 `server/runners/` 增加 Runner  
3. 在 `registry.load_runners()` 里 `register(...)`
