#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")
ROLES_PY = os.path.join(BASE_DIR, "scripts", "studio_roles.py")
ACTIVE_PY = os.path.join(BASE_DIR, "scripts", "studio_active_roles.py")
ACTIONS_PY = os.path.join(BASE_DIR, "scripts", "studio_next_actions.py")


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {"tasks": []}
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="refresh agent plan, active roles and next actions for tasks")
    parser.add_argument("--task-id")
    args = parser.parse_args()

    tasks = load_tasks().get("tasks", [])
    target_ids = [args.task_id] if args.task_id else [t["id"] for t in tasks]
    refreshed = []
    for task_id in target_ids:
        subprocess.run([sys.executable, ROLES_PY, task_id], check=True, capture_output=True, text=True)
        subprocess.run([sys.executable, ACTIVE_PY, task_id], check=True, capture_output=True, text=True)
        subprocess.run([sys.executable, ACTIONS_PY, task_id], check=True, capture_output=True, text=True)
        refreshed.append(task_id)
    print(json.dumps({"refreshed": refreshed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
