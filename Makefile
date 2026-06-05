.PHONY: studio api api-py web dev

# LangGraph Studio 调试（Python，后续可换 JS CLI）
studio:
	langgraph dev --port 2024

# Node.js + LangGraph.js 后端（默认）
api:
	cd apps/server && npm run dev

# Next.js 前端
web:
	cd apps/web && npm run dev

# 同时启动 API (:8000) + Web (:3000)，Ctrl+C 一并退出
dev:
	@echo "API  http://127.0.0.1:8000"
	@echo "Web  http://127.0.0.1:3000"
	@trap 'kill 0' INT TERM; \
		(cd apps/server && npm run dev) & \
		(cd apps/web && npm run dev) & \
		wait

# 旧 Python FastAPI 后端（备用）
api-py:
	uvicorn api.main:app --reload --port 8000
