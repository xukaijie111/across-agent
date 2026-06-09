#!/usr/bin/env bash
# 兼容旧命令，转发到 deploy-aliyun.sh
exec "$(cd "$(dirname "$0")" && pwd)/deploy-aliyun.sh" "$@"
