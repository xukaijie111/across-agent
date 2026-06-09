#!/usr/bin/env bash
# 从本机同步代码到 ECS 并执行 deploy/setup-server.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${ECS_HOST:-106.15.5.36}"
USER="${ECS_USER:-root}"
REMOTE_DIR="/opt/agent-playground"
SSH_OPTS="-o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no"

if [[ -z "${ECS_PASSWORD:-}" ]]; then
  echo "请设置环境变量 ECS_PASSWORD" >&2
  exit 1
fi

TARBALL="/tmp/agent-playground.tgz"

run_remote() {
  expect <<EOF
set timeout -1
spawn ssh ${SSH_OPTS} ${USER}@${HOST} "$1"
expect {
  "password:" { send "${ECS_PASSWORD}\r"; exp_continue }
  eof
}
EOF
}

echo "==> 打包并同步到 ${HOST}:${REMOTE_DIR}"
tar czf "${TARBALL}" -C "${ROOT}" \
  --exclude='.git' --exclude='.venv' --exclude='venv' --exclude='node_modules' \
  --exclude='web-h5/dist' --exclude='data/*.sqlite' --exclude='data/*.db' --exclude='.cursor' .

expect <<EOF
set timeout 120
spawn ssh ${SSH_OPTS} ${USER}@${HOST} "mkdir -p ${REMOTE_DIR}"
expect "password:" { send "${ECS_PASSWORD}\r"; exp_continue }
eof
EOF

expect <<EOF
set timeout 120
spawn scp ${SSH_OPTS} ${TARBALL} ${USER}@${HOST}:${REMOTE_DIR}/agent-playground.tgz
expect "password:" { send "${ECS_PASSWORD}\r"; exp_continue }
eof
EOF

run_remote "cd ${REMOTE_DIR} && tar xzf agent-playground.tgz && rm -f agent-playground.tgz"
rm -f "${TARBALL}"

if [[ -f "${ROOT}/.env" ]]; then
  echo "==> 同步 .env（含 LLM Key，勿提交 git）"
  expect <<EOF
set timeout 60
spawn scp ${SSH_OPTS} ${ROOT}/.env ${USER}@${HOST}:${REMOTE_DIR}/.env
expect {
  "password:" { send "${ECS_PASSWORD}\r"; exp_continue }
  eof
}
EOF
fi

echo "==> 远程安装与配置"
run_remote "chmod +x ${REMOTE_DIR}/deploy/setup-server.sh && ${REMOTE_DIR}/deploy/setup-server.sh"

echo "==> 部署完成，访问 http://${HOST}"
