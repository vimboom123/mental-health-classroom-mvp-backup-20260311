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
ADAPTER_PY = os.path.join(BASE_DIR, "scripts", "studio_agent_adapter.py")
REAL_PY = os.path.join(BASE_DIR, "scripts", "studio_dispatch_real.py")
COLLECT_PY = os.path.join(BASE_DIR, "scripts", "studio_dispatch_collect.py")


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
    parser = argparse.ArgumentParser(description="run one dispatch item and collect result when possible")
    parser.add_argument("task_id")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")

    # 如果已经有 running 项，优先 collect，不再重复 queue-next
    running_item = next((item for item in (task.get("dispatch_plan") or []) if item.get("status") == "running"), None)
    if running_item and running_item.get("output_path"):
        subprocess.run([sys.executable, COLLECT_PY, args.task_id, running_item['id'], running_item['output_path']], check=True)
        print(json.dumps({"task_id": args.task_id, "collected": running_item['id']}, ensure_ascii=False, indent=2))
        return

    subprocess.run([sys.executable, QUEUE_PY, "queue-next", args.task_id], check=True, capture_output=True, text=True)
    data = load_tasks()
    task = find_task(data, args.task_id)

    current = next((item for item in (task.get("dispatch_plan") or []) if item.get("status") == "queued"), None)
    if not current:
        print(json.dumps({"task_id": args.task_id, "ran": None}, ensure_ascii=False, indent=2))
        return

    subprocess.run([sys.executable, QUEUE_PY, "update", args.task_id, current["id"], "running"], check=True, capture_output=True, text=True)

    adapter = subprocess.check_output([
        sys.executable, ADAPTER_PY,
        "--agent", current.get("agent") or "main",
        "--goal", task.get("goal") or "",
        "--phase", task.get("phase") or "",
        "--instruction", current.get("instruction") or "",
    ], text=True)
    real = subprocess.check_output([
        sys.executable, REAL_PY,
        "--agent", current.get("agent") or "main",
        "--goal", task.get("goal") or "",
        "--phase", task.get("phase") or "",
        "--instruction", current.get("instruction") or "",
    ], text=True)
    real_payload = json.loads(real)

    execution_record = {
        "time": now_iso(),
        "dispatch_id": current["id"],
        "agent": current.get("agent"),
        "kind": current.get("kind"),
        "instruction": current.get("instruction"),
        "adapter_payload": json.loads(adapter),
        "real_payload": real_payload,
        "mode": "adapter+real-wrapper" if real_payload.get('supported') else "adapter-placeholder",
    }

    data = load_tasks()
    task = find_task(data, args.task_id)
    task.setdefault("dispatch_runs", []).append(execution_record)
    for item in task.get("dispatch_plan") or []:
        if item.get("id") == current["id"] and real_payload.get('output_path'):
            item['output_path'] = real_payload['output_path']
    for item in task.get("dispatch_history") or []:
        if item.get("id") == current["id"] and real_payload.get('output_path'):
            item['output_path'] = real_payload['output_path']
    save_tasks(data)

    if real_payload.get('supported') and real_payload.get('output_path'):
        subprocess.run([sys.executable, COLLECT_PY, args.task_id, current['id'], real_payload['output_path']], check=True)
    else:
        subprocess.run([sys.executable, QUEUE_PY, "update", args.task_id, current["id"], "done", "--note", "placeholder dispatch completed"], check=True)

    print(json.dumps({"task_id": args.task_id, "ran": execution_record}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
