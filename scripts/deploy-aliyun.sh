#!/usr/bin/env bash
# 一键部署到阿里云 ECS
#
# 首次部署:
#   cp deploy/ecs.env.example deploy/ecs.env   # 填写 ECS_HOST、ECS_PASSWORD 等
#   ./scripts/deploy-aliyun.sh
#
# 仅更新代码（已装过环境）:
#   ./scripts/deploy-aliyun.sh --update
#
# 环境变量（也可写在 deploy/ecs.env）:
#   ECS_HOST  ECS_USER  ECS_PORT  ECS_PASSWORD  ECS_REMOTE_DIR  DEPLOY_DOMAIN
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/deploy/ecs.env"
TARBALL="${TMPDIR:-/tmp}/agent-playground-$$.tgz"

MODE="full"
DRY_RUN=0

usage() {
  cat <<'EOF'
用法: ./scripts/deploy-aliyun.sh [选项]

选项:
  --update      增量部署（不装系统包 / 不重装 MySQL，只同步代码并重启）
  --full        全量安装（默认，适合新机器）
  --dry-run     只打包，不上传
  -h, --help    显示帮助

配置:
  deploy/ecs.env          推荐：复制 ecs.env.example 后填写
  环境变量 ECS_HOST 等    可覆盖 ecs.env

示例:
  cp deploy/ecs.env.example deploy/ecs.env
  ./scripts/deploy-aliyun.sh

  ECS_PASSWORD='你的密码' ./scripts/deploy-aliyun.sh --update
EOF
}

for arg in "$@"; do
  case "$arg" in
    --update) MODE="update" ;;
    --full) MODE="full" ;;
    --dry-run) DRY_RUN=1 ;;
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

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
fi

HOST="${ECS_HOST:-}"
USER="${ECS_USER:-root}"
PORT="${ECS_PORT:-22}"
REMOTE_DIR="${ECS_REMOTE_DIR:-/opt/agent-playground}"
PASSWORD="${ECS_PASSWORD:-}"

if [[ -z "${HOST}" ]]; then
  echo "请设置 ECS_HOST（在 deploy/ecs.env 或环境变量）" >&2
  exit 1
fi

SSH_BASE=(ssh -p "${PORT}" -o StrictHostKeyChecking=accept-new)
SCP_BASE=(scp -P "${PORT}" -o StrictHostKeyChecking=accept-new)

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "缺少命令: $1" >&2
    exit 1
  }
}

need_cmd tar
need_cmd ssh
need_cmd scp

ssh_test_key() {
  "${SSH_BASE[@]}" -o BatchMode=yes -o ConnectTimeout=8 "${USER}@${HOST}" "echo ok" >/dev/null 2>&1
}

run_ssh() {
  local cmd="$1"
  if [[ -n "${PASSWORD}" ]]; then
    need_cmd expect
    expect <<EOF
set timeout -1
spawn ${SSH_BASE[*]} ${USER}@${HOST} "$cmd"
expect {
  -nocase "password:" { send "${PASSWORD}\r"; exp_continue }
  eof
}
EOF
  else
    "${SSH_BASE[@]}" "${USER}@${HOST}" "$cmd"
  fi
}

run_scp() {
  local src="$1"
  local dst="$2"
  if [[ -n "${PASSWORD}" ]]; then
    need_cmd expect
    expect <<EOF
set timeout -1
spawn ${SCP_BASE[*]} "$src" ${USER}@${HOST}:$dst
expect {
  -nocase "password:" { send "${PASSWORD}\r"; exp_continue }
  eof
}
EOF
  else
    "${SCP_BASE[@]}" "$src" "${USER}@${HOST}:${dst}"
  fi
}

if [[ -z "${PASSWORD}" ]] && ! ssh_test_key; then
  echo "SSH 密钥登录失败，请配置 deploy/ecs.env 中的 ECS_PASSWORD 或本机 SSH 密钥" >&2
  exit 1
fi

echo "==> 打包项目"
tar czf "${TARBALL}" -C "${ROOT}" \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='node_modules' \
  --exclude='web-h5/dist' \
  --exclude='data/*.sqlite' \
  --exclude='data/*.db' \
  --exclude='.cursor' \
  --exclude='deploy/ecs.env' \
  .

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "==> dry-run 完成，包位于 ${TARBALL}"
  exit 0
fi

echo "==> 上传到 ${USER}@${HOST}:${REMOTE_DIR}"
run_ssh "mkdir -p ${REMOTE_DIR}"
run_scp "${TARBALL}" "${REMOTE_DIR}/agent-playground.tgz"
rm -f "${TARBALL}"

run_ssh "cd ${REMOTE_DIR} && tar xzf agent-playground.tgz && rm -f agent-playground.tgz"

if [[ -f "${ROOT}/.env" ]]; then
  echo "==> 同步根目录 .env（LLM Key，勿提交 git）"
  LOCAL_MYSQL_PW="$(grep '^MYSQL_PASSWORD=' "${ROOT}/.env" 2>/dev/null | cut -d= -f2- || true)"
  if [[ -z "${LOCAL_MYSQL_PW}" ]]; then
    run_ssh "grep '^MYSQL_PASSWORD=' ${REMOTE_DIR}/.env 2>/dev/null > /tmp/keep-mysql.env || true"
  fi
  run_scp "${ROOT}/.env" "${REMOTE_DIR}/.env"
  if [[ -z "${LOCAL_MYSQL_PW}" ]]; then
    run_ssh "pw=\$(grep '^MYSQL_PASSWORD=' /tmp/keep-mysql.env 2>/dev/null | cut -d= -f2-); if [ -n \"\$pw\" ]; then sed -i \"s/^MYSQL_PASSWORD=.*/MYSQL_PASSWORD=\$pw/\" ${REMOTE_DIR}/.env; fi; rm -f /tmp/keep-mysql.env"
  fi
fi

REMOTE_SETUP="export APP_ROOT=${REMOTE_DIR}"
if [[ -n "${DEPLOY_DOMAIN:-}" ]]; then
  REMOTE_SETUP+=" DEPLOY_DOMAIN='${DEPLOY_DOMAIN}'"
fi

if [[ "${MODE}" == "update" ]]; then
  echo "==> 远程增量更新"
  run_ssh "${REMOTE_SETUP} && chmod +x ${REMOTE_DIR}/deploy/update-server.sh && ${REMOTE_DIR}/deploy/update-server.sh"
else
  echo "==> 远程全量安装"
  run_ssh "${REMOTE_SETUP} && chmod +x ${REMOTE_DIR}/deploy/setup-server.sh && ${REMOTE_DIR}/deploy/setup-server.sh"
fi

echo ""
echo "========================================"
echo " 部署完成 (${MODE})"
if [[ -n "${DEPLOY_DOMAIN:-}" ]]; then
  echo " 访问: http://${DEPLOY_DOMAIN}"
else
  echo " 访问: http://${HOST}"
fi
echo " API : http://${HOST}/api/agents"
echo "========================================"
