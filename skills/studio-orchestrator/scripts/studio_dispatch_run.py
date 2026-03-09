#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")
QUEUE_PY = os.path.join(BASE_DIR, "scripts", "studio_dispatch_queue.py")


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {"tasks": []}
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_task(data, task_id):
    for task in data.get("tasks", []):
        if task.get("id") == task_id:
            return task
    return None


def main():
    parser = argparse.ArgumentParser(description="minimal dispatch runner for studio tasks")
    parser.add_argument("task_id")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")

    subprocess.run([sys.executable, QUEUE_PY, "queue-next", args.task_id], check=True, capture_output=True, text=True)
    data = load_tasks()
    task = find_task(data, args.task_id)

    current = None
    for item in task.get("dispatch_plan") or []:
        if item.get("status") == "queued":
            current = item
            break

    if not current:
        print(json.dumps({"task_id": args.task_id, "ran": None}, ensure_ascii=False, indent=2))
        return

    subprocess.run([sys.executable, QUEUE_PY, "update", args.task_id, current["id"], "running"], check=True, capture_output=True, text=True)

    # 这里先做最小可运行占位：生成 execution record，后续再对接真实 agent/reviewer 调用。
    execution_record = {
        "time": now_iso(),
        "dispatch_id": current["id"],
        "agent": current.get("agent"),
        "kind": current.get("kind"),
        "instruction": current.get("instruction"),
        "mode": "placeholder",
    }

    data = load_tasks()
    task = find_task(data, args.task_id)
    task.setdefault("dispatch_runs", []).append(execution_record)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    subprocess.run([sys.executable, QUEUE_PY, "update", args.task_id, current["id"], "done", "--note", "placeholder dispatch completed"], check=True)
    print(json.dumps({"task_id": args.task_id, "ran": execution_record}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
