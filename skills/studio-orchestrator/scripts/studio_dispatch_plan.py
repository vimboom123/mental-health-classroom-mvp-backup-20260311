#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")

DISPATCH_KIND = {
    "codex": "implementation",
    "gemini": "expression",
    "claude-code": "review",
    "oracle": "second-opinion",
    "qwen": "cn-review",
    "main": "orchestration",
}


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


def stable_id(task, action):
    phase = task.get("phase") or "unknown"
    role = (action.get("role") or "role").replace("_", "-")
    agent = (action.get("agent") or "agent").replace("_", "-")
    return f"{task['id']}-{phase}-{role}-{agent}"


def build_active_plan(task):
    if task.get('status') == 'done' or task.get('phase') == 'done':
        return []
    existing = {item.get("id"): item for item in (task.get("dispatch_history") or [])}
    items = []
    for action in task.get("next_actions") or []:
        item_id = stable_id(task, action)
        prev = existing.get(item_id, {})
        items.append({
            "id": item_id,
            "agent": action.get("agent"),
            "kind": DISPATCH_KIND.get(action.get("agent"), "general"),
            "role": action.get("role"),
            "phase": task.get("phase"),
            "instruction": action.get("action"),
            "status": prev.get("status", "planned"),
            "updated_at": prev.get("updated_at"),
            "note": prev.get("note"),
        })
    return items


def merge_history(task, active_items):
    history = task.get("dispatch_history") or []
    by_id = {item.get("id"): item for item in history}
    for item in active_items:
        existing = by_id.get(item["id"])
        if existing:
            existing.update({k: v for k, v in item.items() if v is not None})
        else:
            history.append(dict(item))
    return history


def main():
    parser = argparse.ArgumentParser(description="build active dispatch plan and preserve full dispatch history")
    parser.add_argument("task_id")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")

    active_plan = build_active_plan(task)
    task["dispatch_plan"] = active_plan
    task["dispatch_history"] = merge_history(task, active_plan)
    task.setdefault("logs", []).append({"time": now_iso(), "message": "dispatch plan refreshed"})
    save_tasks(data)
    print(json.dumps({"task_id": task["id"], "dispatch_plan": active_plan, "dispatch_history": task["dispatch_history"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
