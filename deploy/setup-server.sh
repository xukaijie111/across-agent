#!/usr/bin/env bash
# 首次全量安装：系统包、MySQL、Python、前端构建、systemd + Nginx
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/agent-playground}"
MYSQL_DB="${MYSQL_DATABASE:-agent_playground}"
MYSQL_USER="${MYSQL_USER:-root}"
ENV_FILE="${APP_ROOT}/.env"

log() { echo "==> $*"; }

set_env_var() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
  else
    echo "${key}=${val}" >> "${ENV_FILE}"
  fi
}

log "安装系统包"
dnf install -y \
  python3.11 python3.11-pip python3.11-devel \
  nodejs npm nginx mysql-server \
  gcc gcc-c++ make openssl-devel libffi-devel

log "启动 MySQL / Nginx"
systemctl enable mysqld nginx
systemctl start mysqld
systemctl start nginx

if [[ ! -f "${ENV_FILE}" ]] && [[ -f "${APP_ROOT}/.env.example" ]]; then
  cp "${APP_ROOT}/.env.example" "${ENV_FILE}"
  log "已从 .env.example 生成 .env，请填写 OPENAI_API_KEY"
fi
touch "${ENV_FILE}"

# 若 .env 已有 MYSQL_PASSWORD 且能连库，则保留
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
if [[ -z "${MYSQL_PASSWORD}" ]] && grep -q '^MYSQL_PASSWORD=.\+' "${ENV_FILE}"; then
  MYSQL_PASSWORD="$(grep '^MYSQL_PASSWORD=' "${ENV_FILE}" | cut -d= -f2-)"
fi
if [[ -z "${MYSQL_PASSWORD}" ]]; then
  MYSQL_PASSWORD="$(openssl rand -base64 18 | tr -d '/+=' | head -c 20)"
fi

log "配置 MySQL"
if mysql -uroot -e "SELECT 1" >/dev/null 2>&1; then
  mysql -uroot <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_PASSWORD}';
CREATE DATABASE IF NOT EXISTS ${MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
FLUSH PRIVILEGES;
SQL
elif mysql -uroot -p"${MYSQL_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; then
  mysql -uroot -p"${MYSQL_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS ${MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
FLUSH PRIVILEGES;
SQL
else
  echo "MySQL root 认证失败，请检查 MYSQL_PASSWORD 或手动初始化 MySQL" >&2
  exit 1
fi

log "写入 MySQL 配置到 .env"
set_env_var MYSQL_HOST "127.0.0.1"
set_env_var MYSQL_PORT "3306"
set_env_var MYSQL_USER "${MYSQL_USER}"
set_env_var MYSQL_PASSWORD "${MYSQL_PASSWORD}"
set_env_var MYSQL_DATABASE "${MYSQL_DB}"

log "Python 虚拟环境 + 依赖"
if [[ ! -d "${APP_ROOT}/.venv" ]]; then
  python3.11 -m venv "${APP_ROOT}/.venv"
fi
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
if [[ -n "${DEPLOY_DOMAIN:-}" ]]; then
  sed "s/server_name _;/server_name ${DEPLOY_DOMAIN};/" \
    "${APP_ROOT}/deploy/nginx-agent-playground.conf" \
    > /etc/nginx/conf.d/agent-playground.conf
else
  cp "${APP_ROOT}/deploy/nginx-agent-playground.conf" /etc/nginx/conf.d/agent-playground.conf
fi
if [[ -f /etc/nginx/conf.d/default.conf ]]; then
  mv -f /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
fi
nginx -t
systemctl reload nginx

if systemctl is-active --quiet firewalld; then
  log "放行 firewalld HTTP"
  firewall-cmd --permanent --add-service=http >/dev/null 2>&1 || true
  firewall-cmd --reload
fi

log "完成"
echo "MYSQL_PASSWORD=${MYSQL_PASSWORD}"
systemctl --no-pager status agent-api | head -12
curl -sf http://127.0.0.1:8000/api/agents | head -c 300 || true
echo ""
