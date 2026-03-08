#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <gemini|oracle|oracle-browser> [args...]" >&2
  exit 2
fi

backend="$1"
shift

case "$backend" in
  gemini)
    exec "$(dirname "$0")/gemini22.sh" "$@"
    ;;
  oracle)
    exec "$(dirname "$0")/oracle22.sh" "$@"
    ;;
  oracle-browser)
    exec "$(dirname "$0")/oracle-browser-auto.sh" "$@"
    ;;
  *)
    echo "Unknown backend: $backend" >&2
    echo "Expected one of: gemini, oracle, oracle-browser" >&2
    exit 2
    ;;
esac
