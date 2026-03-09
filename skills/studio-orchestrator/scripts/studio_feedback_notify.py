#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEEDBACK_PY = os.path.join(BASE_DIR, "scripts", "studio_feedback.py")
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {"tasks": []}
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def target_for(task_id, tasks):
    for t in tasks.get("tasks", []):
        if t.get("id") == task_id:
            notify = t.get("notify") or {}
            return notify.get("channel") or "telegram", notify.get("target")
    return "telegram", None


def main():
    parser = argparse.ArgumentParser(description="send progress feedback messages for studio tasks")
    parser.add_argument("--task-id")
    parser.add_argument("--min-interval", type=int, default=600)
    parser.add_argument("--min-progress-step", type=int, default=10)
    args = parser.parse_args()

    cmd = [sys.executable, FEEDBACK_PY, "--json", "--mark-sent", "--min-interval", str(args.min_interval), "--min-progress-step", str(args.min_progress_step)]
    if args.task_id:
        cmd.extend(["--task-id", args.task_id])
    payloads = json.loads(subprocess.check_output(cmd, text=True))
    tasks = load_tasks()
    sent = 0
    for item in payloads:
        channel, target = target_for(item["task_id"], tasks)
        if not target:
            continue
        subprocess.run([
            "/Users/vimboom/.npm-global/bin/openclaw",
            "message",
            "send",
            "--channel", channel,
            "--target", str(target),
            "--message", item["text"],
        ], check=True)
        sent += 1
    print(json.dumps({"sent": sent}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
