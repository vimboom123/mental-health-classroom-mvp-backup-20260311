#!/usr/bin/env python3
import argparse
import json
import os

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


def build_plan(task):
    items = []
    for idx, action in enumerate(task.get("next_actions") or [], start=1):
        items.append({
            "id": f"{task['id']}-step-{idx}",
            "agent": action.get("agent"),
            "kind": DISPATCH_KIND.get(action.get("agent"), "general"),
            "role": action.get("role"),
            "instruction": action.get("action"),
            "status": "planned",
        })
    return items


def main():
    parser = argparse.ArgumentParser(description="build a dispatch plan from next actions")
    parser.add_argument("task_id")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")

    plan = build_plan(task)
    task["dispatch_plan"] = plan
    save_tasks(data)
    print(json.dumps({"task_id": task["id"], "dispatch_plan": plan}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
