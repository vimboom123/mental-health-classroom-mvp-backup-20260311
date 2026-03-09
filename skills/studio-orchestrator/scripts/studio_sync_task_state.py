#!/usr/bin/env python3
import argparse
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")


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
    for t in data.get("tasks", []):
        if t.get("id") == task_id:
            return t
    return None


def sync(task):
    progress = task.setdefault("progress", {})
    phase = task.get("phase")
    status = task.get("status")
    changed = []

    if status == "done":
        if phase != "done":
            task["phase"] = "done"
            changed.append("phase->done")
        progress["percent"] = 100
        progress["status_text"] = "当前阶段：done"
        changed.append("progress->100")
    else:
        if phase == "done":
            task["phase"] = "report"
            changed.append("phase done->report")
        if progress.get("percent", 0) >= 100:
            progress["percent"] = 90
            changed.append("progress 100->90")
        if progress.get("status_text") == "当前阶段：done":
            progress["status_text"] = f"当前阶段：{task.get('phase')}"
            changed.append("status_text sync")
    return changed


def main():
    parser = argparse.ArgumentParser(description="repair inconsistent task status/progress/phase")
    parser.add_argument("task_id")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")
    changed = sync(task)
    save_tasks(data)
    print(json.dumps({"task_id": task["id"], "changed": changed, "task": task}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
