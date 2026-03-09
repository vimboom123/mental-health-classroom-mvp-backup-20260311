#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK_PY = os.path.join(BASE_DIR, "scripts", "studio_task.py")
RUNNER_PY = os.path.join(BASE_DIR, "scripts", "studio_runner.py")


def main():
    parser = argparse.ArgumentParser(description="create a studio task and hand it to runner")
    parser.add_argument("title")
    parser.add_argument("type", choices=["doc", "code", "engineering", "general"])
    parser.add_argument("goal")
    parser.add_argument("--watch-file", action="append")
    parser.add_argument("--watch-process-log", action="append")
    parser.add_argument("--notify-target")
    parser.add_argument("--notify-channel", default="telegram")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        TASK_PY,
        "create",
        "--title",
        args.title,
        "--type",
        args.type,
        "--goal",
        args.goal,
        "--status",
        "in_progress",
        "--phase",
        "intake",
        "--next",
        "runner 接管任务并进入首轮推进",
        "--owner",
        "main-agent",
        "--log",
        "studio_start: task created and handed to runner",
    ]
    for path in args.watch_file or []:
        cmd.extend(["--watch-file", path])
    for path in args.watch_process_log or []:
        cmd.extend(["--watch-process-log", path])
    if args.notify_target:
        cmd.extend(["--notify-target", args.notify_target, "--notify-channel", args.notify_channel])
    task_id = subprocess.check_output(cmd, text=True).strip()
    print(f"TASK_ID={task_id}")
    roles_py = os.path.join(BASE_DIR, "scripts", "studio_roles.py")
    subprocess.run([sys.executable, roles_py, task_id], check=True)
    subprocess.run([sys.executable, RUNNER_PY, "tick", "--verbose"], check=True)


if __name__ == "__main__":
    main()
