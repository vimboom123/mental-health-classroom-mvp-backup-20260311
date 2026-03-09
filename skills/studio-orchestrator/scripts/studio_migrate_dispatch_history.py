#!/usr/bin/env python3
import argparse
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")
LEGACY_RE = re.compile(r"-step-\d+$")


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {"tasks": []}
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(data):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def migrate_task(task):
    history = task.get("dispatch_history") or []
    changed = []
    for item in history:
        item_id = item.get("id", "")
        if LEGACY_RE.search(item_id):
            item["legacy"] = True
            if "phase" not in item:
                item["phase"] = "legacy"
            changed.append(item_id)
    return changed


def main():
    parser = argparse.ArgumentParser(description="mark legacy dispatch history entries and preserve them during stable-id migration")
    parser.add_argument("--task-id")
    args = parser.parse_args()

    data = load_tasks()
    tasks = data.get("tasks", [])
    if args.task_id:
        tasks = [t for t in tasks if t.get("id") == args.task_id]

    report = {}
    for task in tasks:
        changed = migrate_task(task)
        if changed:
            report[task["id"]] = changed
    save_tasks(data)
    print(json.dumps({"migrated": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
