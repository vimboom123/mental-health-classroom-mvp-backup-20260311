#!/usr/bin/env bash
set -euo pipefail

# Fetch a project snapshot from the Notion studio projects data source by exact title match.
# Usage:
#   scripts/notion_project_snapshot.sh "S.H.I.T 风格中文论文重打磨"

PROJECT_NAME="${1:-}"
if [[ -z "$PROJECT_NAME" ]]; then
  echo "Usage: $0 <project-name>" >&2
  exit 2
fi

if [[ ! -f ~/.config/notion/api_key ]]; then
  echo "NOTION_API_KEY_MISSING" >&2
  exit 3
fi

NOTION_KEY=$(cat ~/.config/notion/api_key)
DATA_SOURCE_ID="478ee9d7-d1db-4dc7-85d8-7663db95d6ca"

payload=$(python3 - "$PROJECT_NAME" <<'PY'
import json, sys
name = sys.argv[1]
print(json.dumps({
  "page_size": 20,
  "filter": {
    "property": "项目",
    "title": {"equals": name}
  }
}, ensure_ascii=False))
PY
)

resp=$(curl -fsSL -X POST "https://api.notion.com/v1/data_sources/${DATA_SOURCE_ID}/query" \
  -H "Authorization: Bearer ${NOTION_KEY}" \
  -H 'Notion-Version: 2025-09-03' \
  -H 'Content-Type: application/json' \
  -d "$payload")

RESP_JSON="$resp" python3 - <<'PY'
import json, os
resp = json.loads(os.environ['RESP_JSON'])
results = resp.get('results', [])
if not results:
    print(json.dumps({"found": False}, ensure_ascii=False, indent=2))
    raise SystemExit(0)
page = results[0]
props = page.get('properties', {})

def rich_text(name):
    arr = props.get(name, {}).get('rich_text', [])
    return ''.join(x.get('plain_text','') for x in arr)

def title(name):
    arr = props.get(name, {}).get('title', [])
    return ''.join(x.get('plain_text','') for x in arr)

def select(name):
    s = props.get(name, {}).get('select')
    return s.get('name','') if s else ''

def multi(name):
    arr = props.get(name, {}).get('multi_select', [])
    return [x.get('name','') for x in arr]

def date(name):
    d = props.get(name, {}).get('date')
    return (d or {}).get('start','') if d else ''

out = {
  "found": True,
  "id": page.get('id',''),
  "url": page.get('url',''),
  "项目": title('项目'),
  "状态": select('状态'),
  "优先级": select('优先级'),
  "负责人": rich_text('负责人'),
  "参与角色": multi('参与角色'),
  "交付物": rich_text('交付物'),
  "风险": rich_text('风险'),
  "备注": rich_text('备注'),
  "下一次汇报": date('下一次汇报')
}
print(json.dumps(out, ensure_ascii=False, indent=2))
PY
