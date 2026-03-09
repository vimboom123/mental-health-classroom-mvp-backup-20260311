#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")
REAL_PY = os.path.join(BASE_DIR, "scripts", "studio_dispatch_real.py")


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {"tasks": []}
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(data):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def find_task(data, task_id):
    for task in data.get("tasks", []):
        if task.get("id") == task_id:
            return task
    return None


def main():
    parser = argparse.ArgumentParser(description="launch real dispatch work without blocking runner")
    parser.add_argument("task_id")
    parser.add_argument("dispatch_id")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")
    item = next((x for x in (task.get('dispatch_plan') or []) if x.get('id') == args.dispatch_id), None)
    if not item:
        raise SystemExit(f"dispatch item not found: {args.dispatch_id}")

    out_dir = os.path.join(BASE_DIR, 'state', 'dispatch-runtime')
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, f"{args.dispatch_id}.json")

    cmd = [
        sys.executable, REAL_PY,
        "--agent", item.get("agent") or "main",
        "--goal", task.get("goal") or "",
        "--phase", task.get("phase") or "",
        "--instruction", item.get("instruction") or "",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate()

    payload = json.loads(stdout) if stdout.strip() else {"supported": False}
    meta = {
        "dispatch_id": args.dispatch_id,
        "task_id": args.task_id,
        "launched_at": now_iso(),
        "returncode": proc.returncode,
        "payload": payload,
        "stderr": stderr,
    }
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write('\n')

    item['runtime_meta'] = meta_path
    save_tasks(data)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
