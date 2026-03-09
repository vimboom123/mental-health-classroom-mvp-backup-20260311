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


def should_feedback(task, min_interval, min_progress_step):
    progress = task.get("progress") or {}
    last_ts = progress.get("last_feedback_ts")
    last_percent = progress.get("last_feedback_percent")
    current_percent = progress.get("percent", 0)
    if last_ts is None:
        return True
    if (now_ts() - float(last_ts)) >= min_interval:
        return True
    if last_percent is None:
        return True
    return abs(int(current_percent) - int(last_percent)) >= min_progress_step


def render(task):
    progress = task.get("progress") or {}
    parts = [f"[{task['id']}] {task['title']}"]
    parts.append(f"进度：{progress.get('percent', 0)}%")
    if progress.get("total"):
        parts.append(f"阶段计数：{progress.get('current', 0)}/{progress.get('total')}")
    if progress.get("status_text"):
        parts.append(f"当前：{progress['status_text']}")
    parts.append(f"状态：{task.get('status')} / 阶段：{task.get('phase')}")
    plan = task.get("agent_plan") or []
    if plan:
        parts.append("分工：" + "；".join(f"{x['agent']}={x['responsibility']}" for x in plan[:3]))
    active = task.get("active_roles") or []
    if active:
        parts.append("当前活跃：" + "；".join(f"{x['agent']}({x['role']})" for x in active))
    actions = task.get("next_actions") or []
    if actions:
        parts.append("动作建议：" + "；".join(f"{x['agent']}→{x['action']}" for x in actions[:3]))
    dispatch = task.get("dispatch_plan") or []
    if dispatch:
        parts.append("派工计划：" + "；".join(f"{x['agent']}[{x['kind']}/{x['status']}]" for x in dispatch[:3]))
    history = task.get("dispatch_history") or []
    done_items = [x for x in history if x.get('status') == 'done' and not x.get('legacy')]
    if done_items:
        parts.append("已完成派工：" + "；".join(f"{x['agent']}[{x['kind']}]" for x in done_items[:3]))
    parts.append(f"下一步：{task.get('next') or '-'}")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="emit ROS2-action-like progress feedback for studio tasks")
    parser.add_argument("--task-id")
    parser.add_argument("--min-interval", type=int, default=600)
    parser.add_argument("--min-progress-step", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mark-sent", action="store_true")
    args = parser.parse_args()

    data = load_tasks()
    tasks = data.get("tasks", [])
    if args.task_id:
        tasks = [t for t in tasks if t.get("id") == args.task_id]

    payloads = []
    changed = False
    for task in tasks:
        if task.get("status") not in {"in_progress", "waiting_reviewer"}:
            continue
        if not should_feedback(task, args.min_interval, args.min_progress_step):
            continue
        payloads.append({
            "task_id": task.get("id"),
            "text": render(task),
        })
        if args.mark_sent:
            progress = task.setdefault("progress", {})
            progress["last_feedback_ts"] = now_ts()
            progress["last_feedback_percent"] = progress.get("percent", 0)
            changed = True

    if changed:
        save_tasks(data)

    if args.json:
        print(json.dumps(payloads, ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(x["text"] for x in payloads))


if __name__ == "__main__":
    main()
