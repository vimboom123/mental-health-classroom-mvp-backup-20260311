#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
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


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def load_text(args, task):
    key = args.source_key or args.session_id or "default"
    offsets = task.setdefault("process_offsets", {})
    if args.stdin:
        text = sys.stdin.read()
        next_offset = offsets.get(key, 0) + len(text)
        return key, text, next_offset
    if args.log_file:
        with open(args.log_file, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        next_offset = len(text)
        return key, text, next_offset
    raise SystemExit("provide --log-file or --stdin")


def already_ingested(task, source_key, fp):
    if not fp:
        return False
    for item in reversed(task.get("process_watch", [])):
        if item.get("source_key") == source_key and item.get("fingerprint") == fp:
            return True
    return False


def ingest(task, source_key, text, next_offset, on_done_phase=None, on_done_next=None):
    fp = fingerprint(text)
    if already_ingested(task, source_key, fp):
        return {"classification": "duplicate", "skipped": True, "fingerprint": fp, "next_offset": next_offset}

    cls = classify(text)
    ts = now_iso()
    task.setdefault("process_offsets", {})
    task["process_offsets"][source_key] = next_offset
    task.setdefault("process_watch", []).append({
        "time": ts,
        "source_key": source_key,
        "classification": cls,
        "fingerprint": fp,
        "offset": next_offset,
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
        task["blocker"] = f"process watch detected issue in source {source_key}"
    task["updated_at"] = ts
    task.setdefault("logs", []).append({
        "time": ts,
        "message": f"process watch: {source_key} => {cls}",
    })
    return {"classification": cls, "skipped": False, "fingerprint": fp, "next_offset": next_offset}


def main():
    parser = argparse.ArgumentParser(description="ingest process/session-like logs into studio task state")
    parser.add_argument("task_id")
    parser.add_argument("session_id", nargs="?")
    parser.add_argument("--log-file")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--source-key")
    parser.add_argument("--on-done-phase")
    parser.add_argument("--on-done-next")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")

    source_key, text, next_offset = load_text(args, task)
    result = ingest(task, source_key, text, next_offset, args.on_done_phase, args.on_done_next)
    save_tasks(data)
    payload = {
        "task_id": args.task_id,
        "source_key": source_key,
        "next_offset": next_offset,
        **result,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
