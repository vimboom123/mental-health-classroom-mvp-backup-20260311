#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from studio_common import task_state_lock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")

PHASE_ROLE_MAP = {
    "doc": {
        "intake": ["main-agent"],
        "review_collect": ["reviewer", "second-opinion", "cn-reviewer"],
        "review_merge": ["main-agent"],
        "revise": ["writer"],
        "polish": ["writer", "cn-reviewer"],
        "final_check": ["reviewer", "second-opinion", "main-agent"],
        "report": ["main-agent", "second-opinion", "cn-reviewer"],
    },
    "code": {
        "intake": ["main-agent"],
        "plan": ["main-agent", "second-opinion"],
        "implement": ["implementer", "frontend"],
        "review": ["reviewer", "second-opinion"],
        "test": ["main-agent", "implementer"],
        "fixup": ["implementer", "reviewer"],
        "report": ["main-agent", "second-opinion", "cn-reviewer"],
    },
    "engineering": {
        "intake": ["main-agent"],
        "investigate": ["executor", "second-opinion"],
        "execute": ["executor"],
        "verify": ["reviewer", "main-agent"],
        "iterate": ["executor", "reviewer"],
        "report": ["main-agent", "second-opinion", "cn-reviewer"],
    },
    "general": {
        "intake": ["main-agent"],
        "execute": ["main-agent"],
        "verify": ["main-agent"],
        "report": ["main-agent"],
    },
}


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


def compute_active_roles(task):
    task_type = task.get("type") or "general"
    phase = task.get("phase") or "intake"
    if task_type == 'doc' and task.get('mode') == 'review_only':
        review_only_map = {
            'intake': ['main-agent'],
            'review_collect': ['reviewer', 'second-opinion', 'cn-reviewer'],
            'review_merge': ['main-agent'],
            'report': ['main-agent', 'second-opinion', 'cn-reviewer'],
        }
        role_names = review_only_map.get(phase, ['main-agent'])
    else:
        role_names = PHASE_ROLE_MAP.get(task_type, PHASE_ROLE_MAP["general"]).get(phase, ["main-agent"])
    plan = task.get("agent_plan") or []
    by_role = {item["role"]: item for item in plan}
    active = [by_role[r] for r in role_names if r in by_role]
    return active


def main():
    parser = argparse.ArgumentParser(description="update active AI roles for current task phase")
    parser.add_argument("task_id")
    args = parser.parse_args()

    with task_state_lock():
        data = load_tasks()
        task = find_task(data, args.task_id)
        if not task:
            raise SystemExit(f"task not found: {args.task_id}")

        active = compute_active_roles(task)
        task["active_roles"] = active
        task.setdefault("logs", []).append({
            "time": now_iso(),
            "message": f"active roles refreshed for phase {task.get('phase')}",
        })
        save_tasks(data)
    print(json.dumps({"task_id": task["id"], "phase": task.get("phase"), "active_roles": active}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
