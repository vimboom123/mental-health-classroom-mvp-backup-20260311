#!/usr/bin/env python3
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")

VALID_STATUS = {
    "queued",
    "in_progress",
    "waiting_reviewer",
    "waiting_user",
    "blocked",
    "done",
    "cancelled",
}


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_store():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump({"tasks": []}, f, ensure_ascii=False, indent=2)


def load_store():
    ensure_store()
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_store(data):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def find_task(data, task_id):
    for task in data["tasks"]:
        if task["id"] == task_id:
            return task
    return None


def cmd_create(args):
    data = load_store()
    task_id = uuid.uuid4().hex[:8]
    ts = now_iso()
    task = {
        "id": task_id,
        "title": args.title,
        "type": args.type,
        "goal": args.goal,
        "status": args.status,
        "phase": args.phase,
        "next": args.next_step,
        "owner": args.owner,
        "artifacts": args.artifact or [],
        "watched_files": args.watch_file or [],
        "notify": {
            "channel": args.notify_channel,
            "target": args.notify_target,
        } if args.notify_target else None,
        "blocker": args.blocker,
        "created_at": ts,
        "updated_at": ts,
        "logs": [
            {
                "time": ts,
                "message": args.log or "task created",
            }
        ],
    }
    data["tasks"].append(task)
    save_store(data)
    print(task_id)


def cmd_list(args):
    data = load_store()
    tasks = data["tasks"]
    if args.status:
        tasks = [t for t in tasks if t["status"] == args.status]
    if args.type:
        tasks = [t for t in tasks if t["type"] == args.type]
    if args.json:
        print(json.dumps(tasks, ensure_ascii=False, indent=2))
        return
    for t in tasks:
        print(f"{t['id']} | {t['status']} | {t['type']} | {t['phase']} | {t['title']}")
        print(f"  next: {t.get('next') or '-'}")
        print(f"  owner: {t.get('owner') or '-'} | updated: {t['updated_at']}")
        if t.get("blocker"):
            print(f"  blocker: {t['blocker']}")


def cmd_show(args):
    data = load_store()
    task = find_task(data, args.task_id)
    if not task:
        sys.exit(f"task not found: {args.task_id}")
    print(json.dumps(task, ensure_ascii=False, indent=2))


def cmd_update(args):
    data = load_store()
    task = find_task(data, args.task_id)
    if not task:
        sys.exit(f"task not found: {args.task_id}")
    changed = False
    for field, value in [
        ("status", args.status),
        ("phase", args.phase),
        ("next", args.next_step),
        ("owner", args.owner),
        ("blocker", args.blocker),
    ]:
        if value is not None:
            task[field] = value
            changed = True
    if args.artifact:
        task.setdefault("artifacts", [])
        task["artifacts"].extend(args.artifact)
        changed = True
    if args.clear_blocker:
        task["blocker"] = None
        changed = True
    if changed:
        task["updated_at"] = now_iso()
        if args.log:
            task.setdefault("logs", []).append({"time": task["updated_at"], "message": args.log})
        save_store(data)
    print(json.dumps(task, ensure_ascii=False, indent=2))


def cmd_log(args):
    data = load_store()
    task = find_task(data, args.task_id)
    if not task:
        sys.exit(f"task not found: {args.task_id}")
    ts = now_iso()
    task.setdefault("logs", []).append({"time": ts, "message": args.message})
    task["updated_at"] = ts
    save_store(data)
    print(ts)


def build_parser():
    p = argparse.ArgumentParser(description="studio orchestrator task registry")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("create")
    c.add_argument("--title", required=True)
    c.add_argument("--type", required=True, choices=["doc", "code", "engineering", "general"])
    c.add_argument("--goal", required=True)
    c.add_argument("--status", default="queued", choices=sorted(VALID_STATUS))
    c.add_argument("--phase", default="intake")
    c.add_argument("--next", dest="next_step", default="")
    c.add_argument("--owner", default="main-agent")
    c.add_argument("--artifact", action="append")
    c.add_argument("--watch-file", action="append")
    c.add_argument("--notify-channel", default="telegram")
    c.add_argument("--notify-target")
    c.add_argument("--blocker")
    c.add_argument("--log")
    c.set_defaults(func=cmd_create)

    l = sub.add_parser("list")
    l.add_argument("--status", choices=sorted(VALID_STATUS))
    l.add_argument("--type", choices=["doc", "code", "engineering", "general"])
    l.add_argument("--json", action="store_true")
    l.set_defaults(func=cmd_list)

    s = sub.add_parser("show")
    s.add_argument("task_id")
    s.set_defaults(func=cmd_show)

    u = sub.add_parser("update")
    u.add_argument("task_id")
    u.add_argument("--status", choices=sorted(VALID_STATUS))
    u.add_argument("--phase")
    u.add_argument("--next", dest="next_step")
    u.add_argument("--owner")
    u.add_argument("--artifact", action="append")
    u.add_argument("--blocker")
    u.add_argument("--clear-blocker", action="store_true")
    u.add_argument("--log")
    u.set_defaults(func=cmd_update)

    g = sub.add_parser("log")
    g.add_argument("task_id")
    g.add_argument("message")
    g.set_defaults(func=cmd_log)

    return p


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
