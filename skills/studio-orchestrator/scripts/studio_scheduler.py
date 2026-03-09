#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")

ACTIVE_STATUSES = {"queued", "in_progress", "waiting_reviewer"}


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


def score(task):
    priority = int(task.get("priority", 50))
    status = task.get("status")
    bonus = 0
    if status == "in_progress":
        bonus += 20
    elif status == "waiting_reviewer":
        bonus += 5
    if task.get("blocked"):
        bonus -= 100
    return priority + bonus


def main():
    parser = argparse.ArgumentParser(description="simple scheduler for studio orchestrator")
    parser.add_argument("--max-active", type=int, default=3)
    args = parser.parse_args()

    data = load_tasks()
    tasks = data.get("tasks", [])
    active = [t for t in tasks if t.get("status") in ACTIVE_STATUSES and t.get("status") != "waiting_user"]
    ranked = sorted(active, key=score, reverse=True)
    allowed_ids = {t["id"] for t in ranked[:args.max_active]}
    ts = now_iso()

    for task in tasks:
        task["scheduler"] = {
            "eligible": task.get("id") in allowed_ids,
            "score": score(task),
            "lastScheduledAt": ts if task.get("id") in allowed_ids else task.get("scheduler", {}).get("lastScheduledAt"),
        }

    save_tasks(data)
    print(json.dumps({
        "max_active": args.max_active,
        "selected": [
            {"id": t["id"], "title": t["title"], "score": score(t)} for t in ranked[:args.max_active]
        ]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
