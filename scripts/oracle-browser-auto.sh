#!/usr/bin/env bash
set -euo pipefail

# Stable Oracle browser wrapper: follow current ChatGPT web model selection
# Usage:
#   scripts/oracle-browser-auto.sh --prompt "你的问题" --file "path/**"

export PATH="/usr/local/opt/node@22/bin:/Users/vimboom/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

REMOTE_CHROME="${ORACLE_REMOTE_CHROME:-127.0.0.1:56584}"
CHATGPT_URL="${ORACLE_CHATGPT_URL:-https://chatgpt.com/}"

exec oracle \
  --engine browser \
  --remote-chrome "$REMOTE_CHROME" \
  --chatgpt-url "$CHATGPT_URL" \
  --browser-model-strategy current \
  "$@"
