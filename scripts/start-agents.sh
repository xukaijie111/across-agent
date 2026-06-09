#!/usr/bin/env bash
# 一键启动 Agent API + H5 调试台
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_DIR="$ROOT/server"
WEB_DIR="$ROOT/web-h5"
ENV_FILE="$ROOT/.env"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
API_HOST="${API_HOST:-0.0.0.0}"
INSTALL_DEPS=0

usage() {
  cat <<EOF
用法: ./scripts/start-agents.sh [选项]

选项:
  --install    启动前安装 Python / npm 依赖
  -h, --help   显示帮助

环境变量:
  API_PORT     API 端口（默认 8000）
  WEB_PORT     H5 端口（默认 5173）
  API_HOST     API 监听地址（默认 0.0.0.0，方便手机访问）

示例:
  ./scripts/start-agents.sh --install
  API_PORT=9000 WEB_PORT=5174 ./scripts/start-agents.sh
EOF
}

for arg in "$@"; do
  case "$arg" in
    --install) INSTALL_DEPS=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令: $1" >&2
    exit 1
  fi
}

need_cmd python3
need_cmd npm

if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  echo "==> 安装 Python 依赖"
  python3 -m pip install -r "$SERVER_DIR/requirements.txt"
  echo "==> 安装前端依赖"
  (cd "$WEB_DIR" && npm install)
else
  if [[ ! -d "$WEB_DIR/node_modules" ]]; then
    echo "未找到 node_modules，自动执行 npm install"
    (cd "$WEB_DIR" && npm install)
  fi
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "警告: 未找到 $ENV_FILE" >&2
  echo "       LLM Agent 需要 OPENAI_API_KEY（及可选 OPENAI_BASE_URL）。" >&2
elif ! grep -q '^OPENAI_API_KEY=.\+' "$ENV_FILE" 2>/dev/null; then
  echo "警告: .env 里可能未配置 OPENAI_API_KEY，服装客服将无法调用大模型。" >&2
fi
if [[ ! -f "$ENV_FILE" ]] || ! grep -q '^MYSQL_HOST=.\+' "$ENV_FILE" 2>/dev/null; then
  echo "警告: 必须配置 MYSQL_HOST / MYSQL_DATABASE / MYSQL_USER，服务依赖 MySQL。" >&2
fi

pick_lan_ip() {
  ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || true
}

LAN_IP="$(pick_lan_ip)"

cleanup() {
  echo ""
  echo "==> 正在停止服务..."
  local pids
  pids="$(jobs -p 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    kill $pids 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "==> 启动 Agent API  http://127.0.0.1:${API_PORT}"
(
  cd "$SERVER_DIR"
  exec python3 -m uvicorn main:app --reload --host "$API_HOST" --port "$API_PORT"
) &

echo "==> 启动 H5 前端    http://127.0.0.1:${WEB_PORT}"
(
  cd "$WEB_DIR"
  exec npm run dev -- --host 0.0.0.0 --port "$WEB_PORT"
) &

sleep 2
echo ""
echo "========================================"
echo " 本机访问:  http://127.0.0.1:${WEB_PORT}"
if [[ -n "$LAN_IP" ]]; then
  echo " 手机访问:  http://${LAN_IP}:${WEB_PORT}"
fi
echo " API 文档:  http://127.0.0.1:${API_PORT}/docs"
echo " Ctrl+C 停止"
echo "========================================"
echo ""

wait
