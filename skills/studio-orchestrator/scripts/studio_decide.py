#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")


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


def decide(task):
    logs = task.get("logs", [])[-8:]
    joined = "\n".join(x.get("message", "") for x in logs).lower()
    status = task.get("status")
    phase = task.get("phase")

    if status in {"blocked", "waiting_user", "done", "cancelled"}:
        return None

    if any(k in joined for k in ["done_signal", "review complete", "已完成", "完成了"]):
        if task.get("type") == "doc" and phase in {"review_collect", "review_merge"}:
            return {"phase": "revise", "status": "in_progress", "next": "根据 reviewer 结果直接改正文", "reason": "done-signal found in recent logs"}
        if task.get("type") == "code" and phase in {"review", "implement"}:
            return {"phase": "test", "status": "in_progress", "next": "根据 reviewer / 实现结果进入测试", "reason": "done-signal found in recent logs"}

    if any(k in joined for k in ["blocked", "failed", "error", "exception", "失败"]):
        return {"status": "blocked", "phase": phase, "next": task.get("next"), "reason": "error-like signal found in recent logs"}

    if any(k in joined for k in ["waiting_signal", "pending", "awaiting", "等待"]):
        return {"status": "waiting_reviewer", "phase": phase, "next": task.get("next") or "等待外部结果返回", "reason": "waiting-like signal found in recent logs"}

    return None


def main():
    parser = argparse.ArgumentParser(description="decide next task state from actual recent signals")
    parser.add_argument("task_id")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")

    decision = decide(task)
    if not decision:
        print(json.dumps({"task_id": args.task_id, "decision": None}, ensure_ascii=False, indent=2))
        return

    ts = now_iso()
    for k in ["status", "phase", "next"]:
        if k in decision and decision[k] is not None:
            task[k] = decision[k]
    task["updated_at"] = ts
    task.setdefault("logs", []).append({
        "time": ts,
        "message": f"decide: {decision['reason']}",
    })
    save_tasks(data)
    print(json.dumps({"task_id": args.task_id, "decision": decision}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
