#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")
RUNNER_STATE_FILE = os.path.join(STATE_DIR, "runner_state.json")
WATCH_PY = os.path.join(BASE_DIR, "scripts", "studio_watch.py")
DECIDE_PY = os.path.join(BASE_DIR, "scripts", "studio_decide.py")
NOTIFY_PY = os.path.join(BASE_DIR, "scripts", "studio_notify.py")


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ensure_store():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump({"tasks": []}, f, ensure_ascii=False, indent=2)
    if not os.path.exists(RUNNER_STATE_FILE):
        with open(RUNNER_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_tick": None, "ticks": 0}, f, ensure_ascii=False, indent=2)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def call_py(script, *args, check=True):
    cmd = [sys.executable, script, *args]
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def ingest_watched_files(task):
    watched = task.get("watched_files") or []
    task_id = task.get("id")
    out = []
    for path in watched:
        if not os.path.exists(path):
            continue
        res = call_py(
            WATCH_PY,
            "ingest",
            task_id,
            path,
            "--on-done-phase",
            infer_done_phase(task),
            "--on-done-next",
            infer_done_next(task),
            check=False,
        )
        out.append({"path": path, "code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()})
    return out


def maybe_decide(task):
    res = call_py(DECIDE_PY, task.get("id"), check=False)
    return {"code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}


def maybe_notify(task, min_interval):
    notify = task.get("notify") or {}
    target = notify.get("target")
    channel = notify.get("channel") or "telegram"
    if not target:
        return None
    res = call_py(NOTIFY_PY, "--task-id", task.get("id"), "--target", str(target), "--channel", channel, "--min-interval", str(min_interval), check=False)
    return {"code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}


def tick_once(verbose=False, notify_min_interval=1800):
    ensure_store()
    runner = load_json(RUNNER_STATE_FILE)
    changed = []
    side_effects = []
    ts = now_iso()

    # refresh after every mutation because watch/decide may update file on disk
    store = load_json(TASKS_FILE)
    for task in store.get("tasks", []):
        task_id = task.get("id")
        status = task.get("status")
        phase = task.get("phase")
        task_type = task.get("type")

        if status in {"done", "cancelled", "waiting_user", "blocked"}:
            notify_res = maybe_notify(task, notify_min_interval)
            if notify_res:
                side_effects.append({"task_id": task_id, "notify": notify_res})
            continue

        watch_res = ingest_watched_files(task)
        if watch_res:
            side_effects.append({"task_id": task_id, "watch": watch_res})

        decide_res = maybe_decide(task)
        if decide_res:
            side_effects.append({"task_id": task_id, "decide": decide_res})

        store = load_json(TASKS_FILE)
        refreshed = next((t for t in store.get("tasks", []) if t.get("id") == task_id), task)
        status = refreshed.get("status")
        phase = refreshed.get("phase")

        if status in {"done", "cancelled", "waiting_user", "blocked"}:
            notify_res = maybe_notify(refreshed, notify_min_interval)
            if notify_res:
                side_effects.append({"task_id": task_id, "notify": notify_res})
            continue

        recommendation = recommend(task_type, phase, status)
        if recommendation:
            new_phase = recommendation.get("phase")
            new_status = recommendation.get("status")
            next_step = recommendation.get("next")
            log_msg = recommendation.get("log")
            if not (new_phase == phase and new_status == status and next_step == refreshed.get("next")):
                call_py(
                    os.path.join(BASE_DIR, "scripts", "studio_task.py"),
                    "update",
                    task_id,
                    "--status", new_status,
                    "--phase", new_phase,
                    "--next", next_step,
                    "--log", log_msg,
                )
                changed.append({
                    "task_id": task_id,
                    "title": refreshed.get("title"),
                    "status": new_status,
                    "phase": new_phase,
                    "next": next_step,
                })
                store = load_json(TASKS_FILE)
                refreshed = next((t for t in store.get("tasks", []) if t.get("id") == task_id), refreshed)

        notify_res = maybe_notify(refreshed, notify_min_interval)
        if notify_res:
            side_effects.append({"task_id": task_id, "notify": notify_res})

    runner["last_tick"] = ts
    runner["ticks"] = int(runner.get("ticks", 0)) + 1
    save_json(RUNNER_STATE_FILE, runner)

    payload = {"time": ts, "changed": changed, "side_effects": side_effects, "ticks": runner["ticks"]}
    if verbose:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(changed, ensure_ascii=False))


def infer_done_phase(task):
    task_type = task.get("type")
    phase = task.get("phase")
    if task_type == "doc" and phase == "review_collect":
        return "review_merge"
    if task_type == "code" and phase in {"implement", "review"}:
        return "test"
    if task_type == "engineering" and phase in {"investigate", "execute"}:
        return "verify"
    return phase or "execute"


def infer_done_next(task):
    task_type = task.get("type")
    if task_type == "doc":
        return "开始并单 reviewer 意见"
    if task_type == "code":
        return "开始测试和回归修正"
    if task_type == "engineering":
        return "开始验证执行结果"
    return "根据新结果继续推进"


def recommend(task_type, phase, status):
    flows = {
        "doc": {
            "intake": ("review_collect", "waiting_reviewer", "等待 reviewer / 子代理结果回流", "runner: doc intake -> review_collect"),
            "review_collect": ("review_merge", "in_progress", "并单 reviewer 意见，生成修改清单", "runner: doc review_collect -> review_merge"),
            "review_merge": ("revise", "in_progress", "根据修改清单持续改正文", "runner: doc review_merge -> revise"),
            "revise": ("polish", "in_progress", "收尾润色并统一口径", "runner: doc revise -> polish"),
            "polish": ("final_check", "in_progress", "做最终检查并准备汇报", "runner: doc polish -> final_check"),
            "final_check": ("report", "in_progress", "输出变更摘要与当前结论", "runner: doc final_check -> report"),
        },
        "code": {
            "intake": ("plan", "in_progress", "拆解实现路径与子任务", "runner: code intake -> plan"),
            "plan": ("implement", "in_progress", "进入实现并联动子代理", "runner: code plan -> implement"),
            "implement": ("review", "waiting_reviewer", "等待 reviewer / CI / 子代理结果", "runner: code implement -> review"),
            "review": ("test", "in_progress", "根据 reviewer 结果修正并测试", "runner: code review -> test"),
            "test": ("fixup", "in_progress", "处理回归问题并收尾", "runner: code test -> fixup"),
            "fixup": ("report", "in_progress", "整理结果、风险与后续项", "runner: code fixup -> report"),
        },
        "engineering": {
            "intake": ("investigate", "in_progress", "先调查现状、约束与可行路径", "runner: engineering intake -> investigate"),
            "investigate": ("execute", "in_progress", "执行当前最优路径", "runner: engineering investigate -> execute"),
            "execute": ("verify", "in_progress", "验证结果并判断是否继续迭代", "runner: engineering execute -> verify"),
            "verify": ("iterate", "in_progress", "若未完成则继续下一轮推进", "runner: engineering verify -> iterate"),
            "iterate": ("report", "in_progress", "整理阶段性产出与阻塞点", "runner: engineering iterate -> report"),
        },
        "general": {
            "intake": ("execute", "in_progress", "进入执行阶段", "runner: general intake -> execute"),
            "execute": ("verify", "in_progress", "验证当前结果", "runner: general execute -> verify"),
            "verify": ("report", "in_progress", "整理汇报", "runner: general verify -> report"),
        },
    }
    flow = flows.get(task_type, {})
    if phase not in flow:
        return None
    new_phase, new_status, next_step, log_msg = flow[phase]
    return {"phase": new_phase, "status": new_status, "next": next_step, "log": log_msg}


def daemon_loop(interval, max_ticks, verbose=False, notify_min_interval=1800):
    ticks = 0
    while True:
        tick_once(verbose=verbose, notify_min_interval=notify_min_interval)
        ticks += 1
        if max_ticks and ticks >= max_ticks:
            break
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="studio orchestrator runner")
    sub = parser.add_subparsers(dest="command", required=True)

    tick = sub.add_parser("tick")
    tick.add_argument("--verbose", action="store_true")
    tick.add_argument("--notify-min-interval", type=int, default=1800)

    daemon = sub.add_parser("daemon")
    daemon.add_argument("--interval", type=int, default=60)
    daemon.add_argument("--max-ticks", type=int, default=0)
    daemon.add_argument("--verbose", action="store_true")
    daemon.add_argument("--notify-min-interval", type=int, default=1800)

    args = parser.parse_args()
    if args.command == "tick":
        tick_once(verbose=args.verbose, notify_min_interval=args.notify_min_interval)
    else:
        daemon_loop(args.interval, args.max_ticks, verbose=args.verbose, notify_min_interval=args.notify_min_interval)


if __name__ == "__main__":
    main()
