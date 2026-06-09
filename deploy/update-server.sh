#!/usr/bin/env bash
# 增量部署：安装依赖、构建前端、重启服务（不装系统包、不改 MySQL 密码）
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/agent-playground}"

log() { echo "==> $*"; }

log "Python 依赖"
"${APP_ROOT}/.venv/bin/pip" install -r "${APP_ROOT}/server/requirements.txt"

log "构建前端"
cd "${APP_ROOT}/web-h5"
npm install
npm run build

log "更新 systemd / Nginx 配置"
cp "${APP_ROOT}/deploy/agent-api.service" /etc/systemd/system/agent-api.service
if [[ -n "${DEPLOY_DOMAIN:-}" ]]; then
  sed "s/server_name _;/server_name ${DEPLOY_DOMAIN};/" \
    "${APP_ROOT}/deploy/nginx-agent-playground.conf" \
    > /etc/nginx/conf.d/agent-playground.conf
else
  cp "${APP_ROOT}/deploy/nginx-agent-playground.conf" /etc/nginx/conf.d/agent-playground.conf
fi

systemctl daemon-reload
systemctl restart agent-api
nginx -t
systemctl reload nginx

log "健康检查"
sleep 1
curl -sf http://127.0.0.1:8000/api/agents | head -c 300 || {
  echo "API 未响应，查看日志: journalctl -u agent-api -n 50" >&2
  exit 1
}
echo ""
log "更新完成"
