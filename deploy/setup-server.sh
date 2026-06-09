#!/usr/bin/env bash
# 在 ECS 上安装依赖、MySQL、构建前端、注册 systemd + nginx
set -euo pipefail

APP_ROOT="/opt/agent-playground"
MYSQL_DB="${MYSQL_DATABASE:-agent_playground}"
MYSQL_USER="${MYSQL_USER:-root}"

log() { echo "==> $*"; }

if [[ -z "${MYSQL_PASSWORD:-}" ]]; then
  MYSQL_PASSWORD="$(openssl rand -base64 18 | tr -d '/+=' | head -c 20)"
fi

log "安装系统包"
dnf install -y \
  python3.11 python3.11-pip python3.11-devel \
  nodejs npm nginx mysql-server \
  gcc gcc-c++ make openssl-devel libffi-devel

log "启动 MySQL / Nginx"
systemctl enable mysqld nginx
systemctl start mysqld
systemctl start nginx

log "配置 MySQL"
if mysql -uroot -e "SELECT 1" >/dev/null 2>&1; then
  mysql -uroot <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_PASSWORD}';
CREATE DATABASE IF NOT EXISTS ${MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
FLUSH PRIVILEGES;
SQL
else
  mysql -uroot -p"${MYSQL_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1 || {
    echo "MySQL root 认证失败，请检查 MYSQL_PASSWORD" >&2
    exit 1
  }
  mysql -uroot -p"${MYSQL_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS ${MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
FLUSH PRIVILEGES;
SQL
fi

log "写入 MySQL 配置到 .env"
ENV_FILE="${APP_ROOT}/.env"
touch "${ENV_FILE}"
grep -q '^MYSQL_HOST=' "${ENV_FILE}" || echo "MYSQL_HOST=127.0.0.1" >> "${ENV_FILE}"
grep -q '^MYSQL_PORT=' "${ENV_FILE}" || echo "MYSQL_PORT=3306" >> "${ENV_FILE}"
sed -i "s/^MYSQL_USER=.*/MYSQL_USER=${MYSQL_USER}/" "${ENV_FILE}" 2>/dev/null || echo "MYSQL_USER=${MYSQL_USER}" >> "${ENV_FILE}"
sed -i "s/^MYSQL_PASSWORD=.*/MYSQL_PASSWORD=${MYSQL_PASSWORD}/" "${ENV_FILE}" 2>/dev/null || echo "MYSQL_PASSWORD=${MYSQL_PASSWORD}" >> "${ENV_FILE}"
sed -i "s/^MYSQL_DATABASE=.*/MYSQL_DATABASE=${MYSQL_DB}/" "${ENV_FILE}" 2>/dev/null || echo "MYSQL_DATABASE=${MYSQL_DB}" >> "${ENV_FILE}"

log "Python 虚拟环境 + 依赖"
python3.11 -m venv "${APP_ROOT}/.venv"
"${APP_ROOT}/.venv/bin/pip" install --upgrade pip
"${APP_ROOT}/.venv/bin/pip" install -r "${APP_ROOT}/server/requirements.txt"

log "构建前端"
cd "${APP_ROOT}/web-h5"
npm install
npm run build

log "注册 systemd"
cp "${APP_ROOT}/deploy/agent-api.service" /etc/systemd/system/agent-api.service
systemctl daemon-reload
systemctl enable agent-api
systemctl restart agent-api

log "配置 Nginx"
cp "${APP_ROOT}/deploy/nginx-agent-playground.conf" /etc/nginx/conf.d/agent-playground.conf
if [[ -f /etc/nginx/conf.d/default.conf ]]; then
  mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
fi
nginx -t
systemctl reload nginx

if systemctl is-active --quiet firewalld; then
  log "放行 firewalld HTTP"
  firewall-cmd --permanent --add-service=http >/dev/null
  firewall-cmd --reload
fi

log "完成"
echo "MYSQL_PASSWORD=${MYSQL_PASSWORD}"
systemctl --no-pager status agent-api | head -15
curl -sf http://127.0.0.1:8000/api/agents | head -c 200 || true
echo ""
