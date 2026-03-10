#!/usr/bin/env python3
import argparse
import json
import os
from studio_common import task_state_lock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")

ACTION_HINTS = {
    "main-agent": "主智能体负责统筹、验收、汇报、必要时拍板升级",
    "implementer": "交给 Codex 做主实现或主执行链路",
    "executor": "交给 Codex 执行工程主链路、脚本化落地",
    "frontend": "交给 Gemini 做前端/表达层/交互层优化",
    "surface": "交给 Gemini 做最终总汇报的表达层、展示层与用户可读性收口",
    "writer": "交给 Gemini 做改写、润色、表达层优化",
    "reviewer": "交给 Claude Code 做审查、找问题、提改进",
    "second-opinion": "交给 Oracle 做全局复盘和第二视角审阅",
    "cn-reviewer": "交给 Qwen 做中文表达、本土化判断、中文汇总",
}


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


def build_actions(task):
    explicit = task.get('pm_active_roles') or task.get('active_switches') or []
    source = explicit if explicit else (task.get("active_roles") or [])
    actions = []
    for role in source:
        role_name = role.get("role")
        switch = role.get('switch')
        base = ACTION_HINTS.get(role_name, f"由 {role.get('agent')} 继续处理当前阶段任务")
        if switch:
            base = f"[{switch}] {base}"
        actions.append({
            "role": role_name,
            "agent": role.get("agent"),
            "action": role.get('action') or base,
            "switch": switch,
            "required": role.get('required'),
        })
    return actions


def main():
    parser = argparse.ArgumentParser(description="derive next actions from current active roles")
    parser.add_argument("task_id")
    args = parser.parse_args()

    with task_state_lock():
        data = load_tasks()
        task = find_task(data, args.task_id)
        if not task:
            raise SystemExit(f"task not found: {args.task_id}")

        actions = build_actions(task)
        task["next_actions"] = actions
        save_tasks(data)
    print(json.dumps({"task_id": task["id"], "next_actions": actions}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
