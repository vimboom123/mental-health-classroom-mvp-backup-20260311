#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")

DONE_PATTERNS = [
    re.compile(r"\bdone\b", re.IGNORECASE),
    re.compile(r"\bcompleted\b", re.IGNORECASE),
    re.compile(r"\bfinished\b", re.IGNORECASE),
    re.compile(r"已完成"),
    re.compile(r"完成了"),
    re.compile(r"review complete", re.IGNORECASE),
]

WAIT_PATTERNS = [
    re.compile(r"\bwaiting\b", re.IGNORECASE),
    re.compile(r"\bpending\b", re.IGNORECASE),
    re.compile(r"等待"),
    re.compile(r"排队"),
]

BLOCK_PATTERNS = [
    re.compile(r"\berror\b", re.IGNORECASE),
    re.compile(r"\bfailed\b", re.IGNORECASE),
    re.compile(r"阻塞"),
    re.compile(r"失败"),
]


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


def classify_text(text):
    for p in BLOCK_PATTERNS:
        if p.search(text):
            return "blocked"
    for p in DONE_PATTERNS:
        if p.search(text):
            return "done_signal"
    for p in WAIT_PATTERNS:
        if p.search(text):
            return "waiting_signal"
    return "neutral"


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def inspect_file(path, max_chars=4000):
    if not os.path.exists(path):
        return {"exists": False, "classification": "missing", "excerpt": "", "fingerprint": None}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read(max_chars)
    return {
        "exists": True,
        "classification": classify_text(text),
        "excerpt": text[-800:],
        "fingerprint": fingerprint(text),
    }


def already_ingested(task, path, fp):
    if not fp:
        return False
    for item in reversed(task.get("watch", [])):
        if item.get("path") == path and item.get("fingerprint") == fp:
            return True
    return False


def cmd_probe(args):
    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")
    result = inspect_file(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_ingest(args):
    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")
    result = inspect_file(args.path)
    ts = now_iso()
    task.setdefault("watch", [])
    fp = result.get("fingerprint")

    if already_ingested(task, args.path, fp):
        payload = {
            "task_id": args.task_id,
            "path": args.path,
            "skipped": True,
            "reason": "same fingerprint already ingested",
            "fingerprint": fp,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    task["watch"].append({
        "time": ts,
        "path": args.path,
        "classification": result["classification"],
        "fingerprint": fp,
    })
    cls = result["classification"]
    if cls == "done_signal":
        task["status"] = "in_progress"
        if args.on_done_phase:
            task["phase"] = args.on_done_phase
        if args.on_done_next:
            task["next"] = args.on_done_next
    elif cls == "waiting_signal":
        task["status"] = "waiting_reviewer"
    elif cls == "blocked":
        task["status"] = "blocked"
        task["blocker"] = f"watch detected issue in {args.path}"
    task["updated_at"] = ts
    task.setdefault("logs", []).append({
        "time": ts,
        "message": f"watch ingest: {os.path.basename(args.path)} => {cls}",
    })
    save_tasks(data)
    print(json.dumps(task, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="probe watched outputs and map them into studio task state")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("probe")
    p.add_argument("task_id")
    p.add_argument("path")
    p.set_defaults(func=cmd_probe)

    i = sub.add_parser("ingest")
    i.add_argument("task_id")
    i.add_argument("path")
    i.add_argument("--on-done-phase")
    i.add_argument("--on-done-next")
    i.set_defaults(func=cmd_ingest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
