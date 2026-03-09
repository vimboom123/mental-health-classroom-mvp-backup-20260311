#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")

DEFAULT_PLANS = {
    "doc": [
        {"role": "main-agent", "agent": "main", "responsibility": "PM / 验收 / 最终汇报 / 结构统筹"},
        {"role": "writer", "agent": "gemini", "responsibility": "表达层、润色、可读性优化"},
        {"role": "reviewer", "agent": "claude-code", "responsibility": "代码/文本审校、问题发现"},
        {"role": "second-opinion", "agent": "oracle", "responsibility": "全局复盘与第二视角"},
        {"role": "cn-reviewer", "agent": "qwen", "responsibility": "中文表达、本土语境、中文总结"},
    ],
    "code": [
        {"role": "main-agent", "agent": "main", "responsibility": "PM / 测试验收 / 最终汇报"},
        {"role": "implementer", "agent": "codex", "responsibility": "后端实现、工程落地、主编码"},
        {"role": "frontend", "agent": "gemini", "responsibility": "前端/表达层/交互层优化"},
        {"role": "reviewer", "agent": "claude-code", "responsibility": "代码审查、风险提示、改进建议"},
        {"role": "second-opinion", "agent": "oracle", "responsibility": "全局复盘与架构第二视角"},
        {"role": "cn-reviewer", "agent": "qwen", "responsibility": "中文文档、中文注释、中文总结"},
    ],
    "engineering": [
        {"role": "main-agent", "agent": "main", "responsibility": "PM / 调度 / 结果整合 / 最终汇报"},
        {"role": "executor", "agent": "codex", "responsibility": "执行主链路、脚本化落地、工程改动"},
        {"role": "surface", "agent": "gemini", "responsibility": "表达层、展示层、说明材料"},
        {"role": "reviewer", "agent": "claude-code", "responsibility": "审核执行结果、找问题"},
        {"role": "second-opinion", "agent": "oracle", "responsibility": "全局复盘与补漏"},
        {"role": "cn-reviewer", "agent": "qwen", "responsibility": "中文语境判断与中文汇总"},
    ],
    "general": [
        {"role": "main-agent", "agent": "main", "responsibility": "统筹执行与汇报"},
    ],
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


def main():
    parser = argparse.ArgumentParser(description="assign studio AI roles for a task")
    parser.add_argument("task_id")
    parser.add_argument("--type")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")

    task_type = args.type or task.get("type") or "general"
    plan = DEFAULT_PLANS.get(task_type, DEFAULT_PLANS["general"])
    task["agent_plan"] = plan
    task.setdefault("logs", []).append({
        "time": now_iso(),
        "message": f"roles assigned for task type {task_type}",
    })
    save_tasks(data)
    print(json.dumps({"task_id": task["id"], "agent_plan": plan}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
