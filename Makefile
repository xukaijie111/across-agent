.PHONY: agent-api agent-web agent-dev deploy deploy-update

deploy:
	./scripts/deploy-aliyun.sh

deploy-update:
	./scripts/deploy-aliyun.sh --update

AGENT_SERVER := server
AGENT_WEB := web-h5

agent-api:
	cd $(AGENT_SERVER) && uvicorn main:app --reload --host 127.0.0.1 --port 8000

agent-web:
	cd $(AGENT_WEB) && npm run dev

agent-dev:
	@echo "API  http://127.0.0.1:8000"
	@echo "H5   http://127.0.0.1:5173"
	@trap 'kill 0' INT TERM; \
		(cd $(AGENT_SERVER) && uvicorn main:app --reload --host 127.0.0.1 --port 8000) & \
		(cd $(AGENT_WEB) && npm run dev) & \
		wait
