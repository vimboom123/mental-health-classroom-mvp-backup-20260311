#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")


def now_ts():
    return datetime.now(timezone.utc).timestamp()


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {"tasks": []}
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_task(data, task_id):
    for t in data.get("tasks", []):
        if t.get("id") == task_id:
            return t
    return None


def to_ts(iso_text):
    if not iso_text:
        return None
    try:
        return datetime.fromisoformat(iso_text).timestamp()
    except Exception:
        return None


def check(task, stall_seconds):
    updated = to_ts(task.get("updated_at"))
    recent_dispatch = None
    for item in task.get("dispatch_plan") or []:
        ts = to_ts(item.get("updated_at"))
        if ts and (recent_dispatch is None or ts > recent_dispatch):
            recent_dispatch = ts
    last_activity = max(x for x in [updated, recent_dispatch] if x is not None) if any(x is not None for x in [updated, recent_dispatch]) else None
    stalled = False if last_activity is None else (now_ts() - last_activity) >= stall_seconds
    return {"stalled": stalled, "last_activity_ts": last_activity, "stall_seconds": stall_seconds}


def main():
    parser = argparse.ArgumentParser(description="detect stalled tasks")
    parser.add_argument("task_id")
    parser.add_argument("--stall-seconds", type=int, default=600)
    args = parser.parse_args()
    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")
    print(json.dumps(check(task, args.stall_seconds), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
