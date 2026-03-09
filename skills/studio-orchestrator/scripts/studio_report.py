#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")


def now_ts():
    return datetime.now(timezone.utc).timestamp()


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


def should_report(task, min_interval_sec):
    last = task.get("last_report_ts")
    if last is None:
        return True
    return (now_ts() - float(last)) >= min_interval_sec


def render(task):
    bits = [
        f"[{task['id']}] {task['title']}",
        f"状态：{task.get('status')} / 阶段：{task.get('phase')}",
        f"下一步：{task.get('next') or '-'}",
    ]
    if task.get("blocker"):
        bits.append(f"阻塞：{task['blocker']}")
    artifacts = task.get("artifacts") or []
    if artifacts:
        bits.append("产物：" + ", ".join(artifacts[:3]))
    return "\n".join(bits)


def main():
    parser = argparse.ArgumentParser(description="render report-worthy studio tasks")
    parser.add_argument("--task-id")
    parser.add_argument("--min-interval", type=int, default=1800)
    args = parser.parse_args()

    data = load_tasks()
    tasks = data.get("tasks", [])
    if args.task_id:
        task = find_task(data, args.task_id)
        tasks = [task] if task else []

    reportable = []
    for task in tasks:
        if not task:
            continue
        if task.get("status") in {"blocked", "waiting_user"}:
            reportable.append(render(task))
            continue
        if task.get("phase") == "report" and should_report(task, args.min_interval):
            reportable.append(render(task))

    print("\n\n".join(reportable))


if __name__ == "__main__":
    main()
