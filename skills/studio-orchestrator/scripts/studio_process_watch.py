#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")

DONE_MARKERS = ["done", "completed", "finished", "review complete", "已完成", "完成了"]
WAIT_MARKERS = ["waiting", "pending", "awaiting", "等待"]
BLOCK_MARKERS = ["error", "failed", "exception", "阻塞", "失败"]


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


def classify(text):
    t = text.lower()
    if any(m.lower() in t for m in BLOCK_MARKERS):
        return "blocked"
    if any(m.lower() in t for m in DONE_MARKERS):
        return "done_signal"
    if any(m.lower() in t for m in WAIT_MARKERS):
        return "waiting_signal"
    return "neutral"


def fetch_process_log(session_id, offset=0, limit=4000):
    cmd = [
        "openclaw",
        "process",
        "log",
        session_id,
        "--offset",
        str(offset),
        "--limit",
        str(limit),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(res.stderr.strip() or res.stdout.strip() or "failed to fetch process log")
    return res.stdout


def ingest(task, session_id, text, on_done_phase=None, on_done_next=None):
    cls = classify(text)
    ts = now_iso()
    task.setdefault("process_watch", []).append({
        "time": ts,
        "session_id": session_id,
        "classification": cls,
    })
    if cls == "done_signal":
        task["status"] = "in_progress"
        if on_done_phase:
            task["phase"] = on_done_phase
        if on_done_next:
            task["next"] = on_done_next
    elif cls == "waiting_signal":
        task["status"] = "waiting_reviewer"
    elif cls == "blocked":
        task["status"] = "blocked"
        task["blocker"] = f"process watch detected issue in session {session_id}"
    task["updated_at"] = ts
    task.setdefault("logs", []).append({
        "time": ts,
        "message": f"process watch: {session_id} => {cls}",
    })
    return cls


def main():
    parser = argparse.ArgumentParser(description="ingest process/session log into studio task state")
    parser.add_argument("task_id")
    parser.add_argument("session_id")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=4000)
    parser.add_argument("--on-done-phase")
    parser.add_argument("--on-done-next")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")

    text = fetch_process_log(args.session_id, offset=args.offset, limit=args.limit)
    cls = ingest(task, args.session_id, text, args.on_done_phase, args.on_done_next)
    save_tasks(data)
    print(json.dumps({"classification": cls, "task_id": args.task_id, "session_id": args.session_id}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
