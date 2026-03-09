#!/usr/bin/env bash
set -euo pipefail

# Fetch X/Twitter trends via Apify actor.
# Usage:
#   APIFY_TOKEN=... scripts/x_trends_apify.sh
#   APIFY_TOKEN=... scripts/x_trends_apify.sh world
#   APIFY_TOKEN=... scripts/x_trends_apify.sh world 20
#
# Output: normalized JSON array
#   [{rank, trend, volume, time, timePeriod, source}]

REGION="${1:-world}"
LIMIT="${2:-20}"
ACTOR="karamelo~twitter-trends-scraper"
TOKEN="${APIFY_TOKEN:-}"

if [[ -z "$TOKEN" ]]; then
  echo "APIFY_TOKEN is required" >&2
  exit 2
fi

# Actor accepts generic region strings; 'world' works in current validation.
INPUT=$(python3 - "$REGION" <<'PY'
import json, sys
region = sys.argv[1]
print(json.dumps({"region": region}))
PY
)

RAW=$(curl -fsSL \
  -X POST \
  -H 'Content-Type: application/json' \
  -d "$INPUT" \
  "https://api.apify.com/v2/acts/${ACTOR}/run-sync-get-dataset-items?token=${TOKEN}")

RAW_JSON="$RAW" python3 - "$LIMIT" <<'PY'
import json, os, sys
limit = int(sys.argv[1])
items = json.loads(os.environ['RAW_JSON'])
out = []
for idx, item in enumerate(items[:limit], 1):
    out.append({
        "rank": idx,
        "trend": item.get("trend", ""),
        "volume": item.get("volume", ""),
        "time": item.get("time", ""),
        "timePeriod": item.get("timePeriod", ""),
        "source": "apify:karamelo/twitter-trends-scraper"
    })
print(json.dumps(out, ensure_ascii=False, indent=2))
PY
