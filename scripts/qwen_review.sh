#!/usr/bin/env bash
set -euo pipefail

# Minimal Qwen reviewer via OpenAI-compatible API.
# Requires:
#   QWEN_API_KEY
# Optional:
#   QWEN_BASE_URL (default DashScope compatible endpoint)
#   QWEN_MODEL (default qwen-plus)
# Usage:
#   scripts/qwen_review.sh "prompt" < input.md

PROMPT="${1:-}"
if [[ -z "$PROMPT" ]]; then
  echo "Usage: $0 <prompt>" >&2
  exit 2
fi

API_KEY="${QWEN_API_KEY:-${DASHSCOPE_API_KEY:-}}"
BASE_URL="${QWEN_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
MODEL="${QWEN_MODEL:-qwen-plus}"

if [[ -z "$API_KEY" ]]; then
  echo "QWEN_API_KEY or DASHSCOPE_API_KEY is required" >&2
  exit 3
fi

INPUT=$(cat)
JSON=$(python3 - "$PROMPT" "$MODEL" <<'PY'
import json, sys, os
prompt = sys.argv[1]
model = sys.argv[2]
content = os.environ.get('QWEN_INPUT','')
print(json.dumps({
  'model': model,
  'messages': [
    {'role': 'system', 'content': 'You are Qwen acting as a Chinese reviewer in a multi-AI studio. Be concrete and concise.'},
    {'role': 'user', 'content': prompt + '\n\n以下是待审文本：\n\n' + content}
  ]
}, ensure_ascii=False))
PY
)

RESP=$(QWEN_INPUT="$INPUT" curl -fsSL "${BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H 'Content-Type: application/json' \
  -d "$JSON")

python3 - "$RESP" <<'PY'
import json, sys
resp = json.loads(sys.argv[1])
print(resp['choices'][0]['message']['content'])
PY
