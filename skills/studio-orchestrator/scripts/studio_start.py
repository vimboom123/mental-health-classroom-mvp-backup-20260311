#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK_PY = os.path.join(BASE_DIR, "scripts", "studio_task.py")
RUNNER_PY = os.path.join(BASE_DIR, "scripts", "studio_runner.py")
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")


def main():
    parser = argparse.ArgumentParser(description="create a studio task and hand it to background runner")
    parser.add_argument("title")
    parser.add_argument("type", choices=["doc", "code", "engineering", "general"])
    parser.add_argument("goal")
    parser.add_argument("--watch-file", action="append")
    parser.add_argument("--watch-process-log", action="append")
    parser.add_argument("--notify-target")
    parser.add_argument("--notify-channel", default="telegram")
    parser.add_argument("--background", action="store_true", default=True)
    args = parser.parse_args()

    cmd = [
        sys.executable, TASK_PY, "create",
        "--title", args.title,
        "--type", args.type,
        "--goal", args.goal,
        "--status", "in_progress",
        "--phase", "intake",
        "--next", "runner 接管任务并进入首轮推进",
        "--owner", "main-agent",
        "--log", "studio_start: task created and handed to runner",
    ]
    for path in args.watch_file or []:
        cmd.extend(["--watch-file", path])
    for path in args.watch_process_log or []:
        cmd.extend(["--watch-process-log", path])
    if args.notify_target:
        cmd.extend(["--notify-target", args.notify_target, "--notify-channel", args.notify_channel])

    task_id = subprocess.check_output(cmd, text=True).strip()
    roles_py = os.path.join(BASE_DIR, "scripts", "studio_roles.py")
    active_roles_py = os.path.join(BASE_DIR, "scripts", "studio_active_roles.py")
    next_actions_py = os.path.join(BASE_DIR, "scripts", "studio_next_actions.py")
    dispatch_plan_py = os.path.join(BASE_DIR, "scripts", "studio_dispatch_plan.py")
    subprocess.run([sys.executable, roles_py, task_id], check=True)
    subprocess.run([sys.executable, active_roles_py, task_id], check=True)
    subprocess.run([sys.executable, next_actions_py, task_id], check=True)
    subprocess.run([sys.executable, dispatch_plan_py, task_id], check=True)

    runtime_meta = {"mode": "background-daemon", "started_by": "studio_start.py"}
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for t in data.get('tasks', []):
            if t.get('id') == task_id:
                t['runtime'] = runtime_meta
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')

    # 非阻塞启动：后台起一轮 daemon，立即返回 task_id
    if args.background:
        subprocess.Popen([
            sys.executable, RUNNER_PY, 'daemon', '--interval', '30', '--max-ticks', '20', '--max-active', '10', '--notify-min-interval', '300'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.run([sys.executable, RUNNER_PY, 'tick', '--verbose'], check=True)

    print(f"TASK_ID={task_id}")


if __name__ == "__main__":
    main()
