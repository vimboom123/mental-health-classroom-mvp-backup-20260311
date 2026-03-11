#!/usr/bin/env python3
import argparse
import json
import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path

from studio_common import BASE_DIR, RUNNER_STATE_FILE, STUDIO_SERVICE_LABEL, now_iso

SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
RUNNER_PY = os.path.join(SCRIPTS_DIR, 'studio_runner.py')
LAUNCH_AGENTS_DIR = os.path.expanduser('~/Library/LaunchAgents')
PLIST_PATH = os.path.join(LAUNCH_AGENTS_DIR, f'{STUDIO_SERVICE_LABEL}.plist')
LOG_DIR = os.path.join(BASE_DIR, 'state', 'logs')
STDOUT_LOG = '/tmp/ai.openclaw.studio-runner.out.log'
STDERR_LOG = '/tmp/ai.openclaw.studio-runner.err.log'
WRAPPER_PATH = os.path.expanduser('~/.local/bin/openclaw-studio-runner-launch.sh')
CLEAN_PATH = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'


def current_gui_domain() -> str:
    return f'gui/{os.getuid()}'


def ensure_dirs() -> None:
    os.makedirs(LAUNCH_AGENTS_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(WRAPPER_PATH), exist_ok=True)


def write_wrapper(interval: int) -> None:
    local_base = os.path.expanduser('~/.openclaw/workspace/skills/studio-orchestrator')
    candidates = []
    for item in [BASE_DIR, local_base]:
        if item and item not in candidates:
            candidates.append(item)
    candidates_literal = '\n'.join([f'  {shlex.quote(c)}' for c in candidates])
    python_bin = sys.executable

    script = f'''#!/bin/zsh
export PATH={CLEAN_PATH!r}
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
PY_BIN={python_bin!r}
CANDIDATES=(
{candidates_literal}
)

ts() {{
  date '+%Y-%m-%dT%H:%M:%S%z'
}}

pick_base_dir() {{
  local candidate=""
  for candidate in "${{CANDIDATES[@]}}"; do
    [[ -z "$candidate" ]] && continue
    if [[ -f "$candidate/scripts/studio_runner.py" ]]; then
      if mkdir -p "$candidate/state" 2>/dev/null; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  return 1
}}

while true; do
  BASE="$(pick_base_dir || true)"
  if [[ -z "$BASE" ]]; then
    echo "$(ts) [studio-runner] no writable base dir found; waiting..." >&2
    sleep {interval}
    continue
  fi
  "$PY_BIN" "$BASE/scripts/studio_runner.py" tick --max-active 10 --notify-min-interval 300 --lock-retries 8 --lock-retry-delay-ms 250
  rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "$(ts) [studio-runner] tick failed base=$BASE code=$rc" >&2
  fi
  sleep {interval}
done
'''
    Path(WRAPPER_PATH).write_text(script, encoding='utf-8')
    os.chmod(WRAPPER_PATH, 0o755)


def plist_payload(interval: int) -> dict:
    return {
        'Label': STUDIO_SERVICE_LABEL,
        'ProgramArguments': [WRAPPER_PATH],
        'WorkingDirectory': os.path.expanduser('~'),
        'RunAtLoad': True,
        'KeepAlive': True,
        'StandardOutPath': STDOUT_LOG,
        'StandardErrorPath': STDERR_LOG,
        'ProcessType': 'Background',
        'EnvironmentVariables': {
            'PATH': CLEAN_PATH,
        },
    }


def install(interval: int) -> None:
    ensure_dirs()
    write_wrapper(interval)
    payload = plist_payload(interval)
    with open(PLIST_PATH, 'wb') as f:
        plistlib.dump(payload, f)


def _run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True)


def is_bootstrapped() -> bool:
    res = _run(['launchctl', 'print', f'{current_gui_domain()}/{STUDIO_SERVICE_LABEL}'])
    return res.returncode == 0


def bootstrap(interval: int) -> None:
    install(interval)
    if is_bootstrapped():
        _run(['launchctl', 'bootout', current_gui_domain(), PLIST_PATH])
    res = _run(['launchctl', 'bootstrap', current_gui_domain(), PLIST_PATH])
    if res.returncode != 0 and 'already loaded' not in (res.stderr or ''):
        sys.exit(res.stderr.strip() or res.stdout.strip() or 'launchctl bootstrap failed')


def kickstart() -> None:
    res = _run(['launchctl', 'kickstart', '-k', f'{current_gui_domain()}/{STUDIO_SERVICE_LABEL}'])
    if res.returncode != 0:
        sys.exit(res.stderr.strip() or res.stdout.strip() or 'launchctl kickstart failed')


def cmd_install(args: argparse.Namespace) -> None:
    install(args.interval)
    print(PLIST_PATH)


def cmd_start(args: argparse.Namespace) -> None:
    bootstrap(args.interval)
    kickstart()
    print(json.dumps({'label': STUDIO_SERVICE_LABEL, 'plist': PLIST_PATH, 'status': 'started'}, ensure_ascii=False, indent=2))


def cmd_stop(args: argparse.Namespace) -> None:
    if is_bootstrapped():
        res = _run(['launchctl', 'bootout', current_gui_domain(), PLIST_PATH])
        if res.returncode != 0:
            sys.exit(res.stderr.strip() or res.stdout.strip() or 'launchctl bootout failed')
    print(json.dumps({'label': STUDIO_SERVICE_LABEL, 'status': 'stopped'}, ensure_ascii=False, indent=2))


def cmd_restart(args: argparse.Namespace) -> None:
    bootstrap(args.interval)
    kickstart()
    print(json.dumps({'label': STUDIO_SERVICE_LABEL, 'status': 'restarted'}, ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    res = _run(['launchctl', 'print', f'{current_gui_domain()}/{STUDIO_SERVICE_LABEL}'])
    running = res.returncode == 0
    runner_state = None
    if os.path.exists(RUNNER_STATE_FILE):
        try:
            runner_state = json.loads(Path(RUNNER_STATE_FILE).read_text(encoding='utf-8'))
        except Exception:
            runner_state = None
    payload = {
        'label': STUDIO_SERVICE_LABEL,
        'plist': PLIST_PATH,
        'wrapper': WRAPPER_PATH,
        'installed': os.path.exists(PLIST_PATH),
        'bootstrapped': running,
        'runner_state': runner_state,
        'checked_at': now_iso(),
    }
    if running:
        payload['launchctl'] = res.stdout.strip()
    else:
        payload['error'] = (res.stderr or res.stdout or '').strip()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_ensure(args: argparse.Namespace) -> None:
    install(args.interval)
    if not is_bootstrapped():
        bootstrap(args.interval)
    kickstart()
    print(json.dumps({'label': STUDIO_SERVICE_LABEL, 'status': 'ensured', 'plist': PLIST_PATH, 'wrapper': WRAPPER_PATH}, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='manage studio runner launchd service')
    sub = parser.add_subparsers(dest='command', required=True)
    for name, func in [
        ('install', cmd_install),
        ('start', cmd_start),
        ('stop', cmd_stop),
        ('restart', cmd_restart),
        ('status', cmd_status),
        ('ensure', cmd_ensure),
    ]:
        sp = sub.add_parser(name)
        sp.add_argument('--interval', type=int, default=30)
        sp.set_defaults(func=func)
    return parser


if __name__ == '__main__':
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
