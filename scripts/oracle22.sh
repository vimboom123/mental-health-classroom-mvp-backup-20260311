#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/opt/node@22/bin:/Users/vimboom/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

args=("$@")
needs_wait=1
has_engine=0
for arg in "${args[@]}"; do
  if [[ "$arg" == "--wait" ]]; then
    needs_wait=0
  fi
  if [[ "$arg" == "--engine" || "$arg" == -e ]]; then
    has_engine=1
  fi
done

prefix=()
if [[ $has_engine -eq 0 ]]; then
  prefix+=(--engine api)
fi
if [[ $needs_wait -eq 1 ]]; then
  prefix+=(--wait)
fi

exec oracle "${prefix[@]}" "${args[@]}"
