#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")

VALID = {"planned", "queued", "running", "done", "failed"}


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


def ensure_ids(task):
    changed = False
    for idx, item in enumerate(task.get("dispatch_plan") or []):
        if "id" not in item:
            item["id"] = f"{task['id']}-step-{idx+1}"
            changed = True
        if "status" not in item:
            item["status"] = "planned"
            changed = True
    task.setdefault("dispatch_history", [])
    return changed


def main():
    parser = argparse.ArgumentParser(description="manage dispatch queue items")
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show")
    show.add_argument("task_id")

    update = sub.add_parser("update")
    update.add_argument("task_id")
    update.add_argument("item_id")
    update.add_argument("status", choices=sorted(VALID))
    update.add_argument("--note")

    queue = sub.add_parser("queue-next")
    queue.add_argument("task_id")

    args = parser.parse_args()
    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")

    ensure_ids(task)

    if args.command == "show":
        print(json.dumps(task.get("dispatch_plan") or [], ensure_ascii=False, indent=2))
        return

    if args.command == "queue-next":
        for item in task.get("dispatch_plan") or []:
            if item.get("status") == "planned":
                item["status"] = "queued"
                item["updated_at"] = now_iso()
                for hist in task.get("dispatch_history") or []:
                    if hist.get("id") == item.get("id"):
                        hist.update(item)
                task.setdefault("logs", []).append({"time": now_iso(), "message": f"dispatch queued: {item['id']}"})
                save_tasks(data)
                print(json.dumps(item, ensure_ascii=False, indent=2))
                return
        print(json.dumps({"queued": None}, ensure_ascii=False, indent=2))
        return

    for item in task.get("dispatch_plan") or []:
        if item.get("id") == args.item_id:
            item["status"] = args.status
            item["updated_at"] = now_iso()
            if args.note:
                item["note"] = args.note
            for hist in task.get("dispatch_history") or []:
                if hist.get("id") == item.get("id"):
                    hist.update(item)
            task.setdefault("logs", []).append({"time": now_iso(), "message": f"dispatch {args.status}: {item['id']}"})
            save_tasks(data)
            print(json.dumps(item, ensure_ascii=False, indent=2))
            return
    raise SystemExit(f"dispatch item not found: {args.item_id}")


if __name__ == "__main__":
    main()
