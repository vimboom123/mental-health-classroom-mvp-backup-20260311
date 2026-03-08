#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/opt/node@22/bin:/Users/vimboom/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
exec oracle "$@"
