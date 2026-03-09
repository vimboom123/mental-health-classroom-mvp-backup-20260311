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
PROCESS_WATCH_PY = os.path.join(BASE_DIR, "scripts", "studio_process_watch.py")
DECIDE_PY = os.path.join(BASE_DIR, "scripts", "studio_decide.py")
SCHEDULER_PY = os.path.join(BASE_DIR, "scripts", "studio_scheduler.py")
NOTIFY_PY = os.path.join(BASE_DIR, "scripts", "studio_notify.py")
FEEDBACK_NOTIFY_PY = os.path.join(BASE_DIR, "scripts", "studio_feedback_notify.py")
ACTIVE_ROLES_PY = os.path.join(BASE_DIR, "scripts", "studio_active_roles.py")
NEXT_ACTIONS_PY = os.path.join(BASE_DIR, "scripts", "studio_next_actions.py")
DISPATCH_PLAN_PY = os.path.join(BASE_DIR, "scripts", "studio_dispatch_plan.py")
COMPLETION_GATE_PY = os.path.join(BASE_DIR, "scripts", "studio_completion_gate.py")
TASK_PY = os.path.join(BASE_DIR, "scripts", "studio_task.py")
SYNC_TASK_PY = os.path.join(BASE_DIR, "scripts", "studio_sync_task_state.py")
STALL_CHECK_PY = os.path.join(BASE_DIR, "scripts", "studio_stall_check.py")

TERMINAL_STATUSES = {"done", "cancelled", "waiting_user", "blocked", "failed"}
ACTIVE_STATUSES = {"queued", "in_progress", "waiting_reviewer"}


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


def infer_progress(task_type, phase):
    phase_orders = {
        "doc": ["intake", "review_collect", "review_merge", "revise", "polish", "final_check", "report", "done"],
        "code": ["intake", "plan", "implement", "review", "test", "fixup", "report", "done"],
        "engineering": ["intake", "investigate", "execute", "verify", "iterate", "report", "done"],
        "general": ["intake", "execute", "verify", "report", "done"],
    }
    order = phase_orders.get(task_type, phase_orders["general"])
    try:
        idx = order.index(phase)
    except ValueError:
        idx = 0
    current = idx + 1
    total = len(order)
    percent = int((current / total) * 100)
    return {"percent": percent, "current": current, "total": total, "status_text": f"当前阶段：{phase}"}


def scheduled_ids(max_active=3):
    res = call_py(SCHEDULER_PY, "--max-active", str(max_active), check=False)
    if res.returncode != 0:
        return None, {"code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}
    payload = json.loads(res.stdout or '{}')
    ids = {item['id'] for item in payload.get('selected', [])}
    return ids, payload


def ingest_watched_files(task):
    watched = task.get("watched_files") or []
    out = []
    for path in watched:
        if not os.path.exists(path):
            continue
        res = call_py(WATCH_PY, "ingest", task["id"], path, "--on-done-phase", infer_done_phase(task), "--on-done-next", infer_done_next(task), check=False)
        out.append({"path": path, "code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()})
    return out


def ingest_watched_process_logs(task):
    watched = task.get("watched_process_logs") or []
    out = []
    for path in watched:
        if not os.path.exists(path):
            continue
        source_key = os.path.basename(path)
        res = call_py(PROCESS_WATCH_PY, task["id"], "--log-file", path, "--source-key", source_key, "--on-done-phase", infer_done_phase(task), "--on-done-next", infer_done_next(task), check=False)
        out.append({"path": path, "source_key": source_key, "code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()})
    return out


def maybe_decide(task):
    res = call_py(DECIDE_PY, task["id"], check=False)
    return {"code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}


def maybe_notify(task, min_interval):
    notify = task.get("notify") or {}
    target = notify.get("target")
    channel = notify.get("channel") or "telegram"
    if not target:
        return None
    res = call_py(NOTIFY_PY, "--task-id", task["id"], "--target", str(target), "--channel", channel, "--min-interval", str(min_interval), check=False)
    return {"code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}


def maybe_feedback_notify(task, min_interval=600, min_progress_step=10):
    notify = task.get("notify") or {}
    if not notify.get("target"):
        return None
    res = call_py(FEEDBACK_NOTIFY_PY, "--task-id", task["id"], "--min-interval", str(min_interval), "--min-progress-step", str(min_progress_step), check=False)
    return {"code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}


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
            "report": ("done", "done", "论文改写任务完成", "runner: doc report -> done"),
        },
        "code": {
            "intake": ("plan", "in_progress", "拆解实现路径与子任务", "runner: code intake -> plan"),
            "plan": ("implement", "in_progress", "进入实现并联动子代理", "runner: code plan -> implement"),
            "implement": ("review", "waiting_reviewer", "等待 reviewer / CI / 子代理结果", "runner: code implement -> review"),
            "review": ("test", "in_progress", "根据 reviewer 结果修正并测试", "runner: code review -> test"),
            "test": ("fixup", "in_progress", "处理回归问题并收尾", "runner: code test -> fixup"),
            "fixup": ("report", "in_progress", "整理结果、风险与后续项", "runner: code fixup -> report"),
            "report": ("done", "done", "代码任务完成", "runner: code report -> done"),
        },
        "engineering": {
            "intake": ("investigate", "in_progress", "先调查现状、约束与可行路径", "runner: engineering intake -> investigate"),
            "investigate": ("execute", "in_progress", "执行当前最优路径", "runner: engineering investigate -> execute"),
            "execute": ("verify", "in_progress", "验证结果并判断是否继续迭代", "runner: engineering execute -> verify"),
            "verify": ("iterate", "in_progress", "若未完成则继续下一轮推进", "runner: engineering verify -> iterate"),
            "iterate": ("report", "in_progress", "整理阶段性产出与阻塞点", "runner: engineering iterate -> report"),
            "report": ("done", "done", "工程任务完成", "runner: engineering report -> done"),
        },
        "general": {
            "intake": ("execute", "in_progress", "进入执行阶段", "runner: general intake -> execute"),
            "execute": ("verify", "in_progress", "验证当前结果", "runner: general execute -> verify"),
            "verify": ("report", "in_progress", "整理汇报", "runner: general verify -> report"),
            "report": ("done", "done", "任务完成", "runner: general report -> done"),
        },
    }
    flow = flows.get(task_type, {})
    if phase not in flow:
        return None
    new_phase, new_status, next_step, log_msg = flow[phase]
    return {"phase": new_phase, "status": new_status, "next": next_step, "log": log_msg}


def completion_gate_ok(task_id):
    res = call_py(COMPLETION_GATE_PY, task_id, check=False)
    if res.returncode != 0:
        return False, {"code": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}
    payload = json.loads(res.stdout or '{}')
    return bool(payload.get('ok')), payload


def apply_recommendation(task_id, task_type, phase, status, next_value):
    recommendation = recommend(task_type, phase, status)
    if not recommendation:
        return None
    new_phase = recommendation["phase"]
    new_status = recommendation["status"]
    next_step = recommendation["next"]
    log_msg = recommendation["log"]

    if new_status == "done":
        ok, gate_payload = completion_gate_ok(task_id)
        if not ok:
            return {"task_id": task_id, "blocked_done": True, "gate": gate_payload}
    if new_phase == phase and new_status == status and next_step == next_value:
        return None
    progress = infer_progress(task_type, new_phase)
    call_py(TASK_PY, "update", task_id, "--status", new_status, "--phase", new_phase, "--next", next_step,
            "--progress-percent", str(progress["percent"]), "--progress-current", str(progress["current"]),
            "--progress-total", str(progress["total"]), "--progress-status", progress["status_text"], "--log", log_msg)
    call_py(ACTIVE_ROLES_PY, task_id, check=False)
    call_py(NEXT_ACTIONS_PY, task_id, check=False)
    call_py(DISPATCH_PLAN_PY, task_id, check=False)
    return {"task_id": task_id, "status": new_status, "phase": new_phase, "next": next_step}


def tick_once(verbose=False, notify_min_interval=1800, max_active=3):
    ensure_store()
    runner = load_json(RUNNER_STATE_FILE)
    changed = []
    side_effects = []
    ts = now_iso()

    allowed_ids, sched_payload = scheduled_ids(max_active=max_active)
    if sched_payload:
        side_effects.append({"scheduler": sched_payload})

    store = load_json(TASKS_FILE)
    for task in store.get("tasks", []):
        task_id = task.get("id")
        status = task.get("status")

        if status in TERMINAL_STATUSES:
            notify_res = maybe_notify(task, notify_min_interval)
            if notify_res:
                side_effects.append({"task_id": task_id, "notify": notify_res})
            continue

        if allowed_ids is not None and task_id not in allowed_ids and status in ACTIVE_STATUSES:
            side_effects.append({"task_id": task_id, "skipped_by_scheduler": True})
            continue

        watch_res = ingest_watched_files(task)
        if watch_res:
            side_effects.append({"task_id": task_id, "watch": watch_res})
        process_watch_res = ingest_watched_process_logs(task)
        if process_watch_res:
            side_effects.append({"task_id": task_id, "process_watch": process_watch_res})
        decide_res = maybe_decide(task)
        if decide_res:
            side_effects.append({"task_id": task_id, "decide": decide_res})

        call_py(SYNC_TASK_PY, task_id, check=False)
        store = load_json(TASKS_FILE)
        refreshed = next((t for t in store.get("tasks", []) if t.get("id") == task_id), task)

        # 核心修正：只要没进入终止/等待用户/阻塞状态，就持续推进直到不能再推进。
        safety = 0
        while refreshed.get("status") not in TERMINAL_STATUSES and safety < 8:
            result = apply_recommendation(
                refreshed["id"],
                refreshed.get("type"),
                refreshed.get("phase"),
                refreshed.get("status"),
                refreshed.get("next"),
            )
            if not result:
                break
            if result.get("blocked_done"):
                side_effects.append(result)
                break
            changed.append(result)
            store = load_json(TASKS_FILE)
            refreshed = next((t for t in store.get("tasks", []) if t.get("id") == task_id), refreshed)
            safety += 1

        # 自动执行 dispatch：planned -> launch, running -> poll collect
        dispatch_items = refreshed.get('dispatch_plan') or []
        launch_py = os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_launch.py')
        poll_py = os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_poll.py')
        for item in dispatch_items:
            if item.get('status') == 'planned':
                queue_res = call_py(os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_queue.py'), 'queue-next', task_id, check=False)
                side_effects.append({"task_id": task_id, "dispatch_queue": {"code": queue_res.returncode, "stdout": queue_res.stdout.strip(), "stderr": queue_res.stderr.strip()}})
                break
        store = load_json(TASKS_FILE)
        refreshed = next((t for t in store.get("tasks", []) if t.get("id") == task_id), refreshed)
        dispatch_items = refreshed.get('dispatch_plan') or []
        for item in dispatch_items:
            if item.get('status') == 'queued':
                update_res = call_py(os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_queue.py'), 'update', task_id, item.get('id'), 'running', check=False)
                launch_res = call_py(launch_py, task_id, item.get('id'), check=False)
                side_effects.append({"task_id": task_id, "dispatch_launch": {"code": launch_res.returncode, "stdout": launch_res.stdout.strip(), "stderr": launch_res.stderr.strip()}, "dispatch_running": {"code": update_res.returncode}})
        store = load_json(TASKS_FILE)
        refreshed = next((t for t in store.get("tasks", []) if t.get("id") == task_id), refreshed)
        for item in refreshed.get('dispatch_plan') or []:
            if item.get('status') == 'running' and item.get('runtime_meta'):
                poll_res = call_py(poll_py, task_id, item.get('id'), check=False)
                side_effects.append({"task_id": task_id, "dispatch_poll": {"code": poll_res.returncode, "stdout": poll_res.stdout.strip(), "stderr": poll_res.stderr.strip()}})
        store = load_json(TASKS_FILE)
        refreshed = next((t for t in store.get("tasks", []) if t.get("id") == task_id), refreshed)

        # 若当前活跃派工全部 done，则自动补一条最终汇报证据，并允许后续进入 completion gate
        active_dispatch = refreshed.get('dispatch_plan') or []
        if active_dispatch and all(x.get('status') == 'done' for x in active_dispatch):
            report_log = '最终汇报：当前活跃派工已完成，进入完成判定'
            call_py(TASK_PY, 'log', task_id, report_log, check=False)
            store = load_json(TASKS_FILE)
            refreshed = next((t for t in store.get("tasks", []) if t.get("id") == task_id), refreshed)

        stall_res = call_py(STALL_CHECK_PY, task_id, "--stall-seconds", "180", check=False)
        if stall_res.returncode == 0:
            stall_payload = json.loads(stall_res.stdout or '{}')
            if stall_payload.get('stalled'):
                side_effects.append({"task_id": task_id, "stalled": stall_payload})

        # 若 report 阶段且 gate 已通过，补做一次 done 推进
        if refreshed.get('phase') == 'report' and refreshed.get('status') == 'in_progress':
            ok, gate_payload = completion_gate_ok(task_id)
            if ok:
                result = apply_recommendation(task_id, refreshed.get('type'), refreshed.get('phase'), refreshed.get('status'), refreshed.get('next'))
                if result and not result.get('blocked_done'):
                    changed.append(result)
                    store = load_json(TASKS_FILE)
                    refreshed = next((t for t in store.get("tasks", []) if t.get("id") == task_id), refreshed)
            else:
                side_effects.append({"task_id": task_id, "gate_wait": gate_payload})

        feedback_res = maybe_feedback_notify(refreshed)
        if feedback_res:
            side_effects.append({"task_id": task_id, "feedback_notify": feedback_res})
        notify_res = maybe_notify(refreshed, notify_min_interval)
        if notify_res:
            side_effects.append({"task_id": task_id, "notify": notify_res})

    runner["last_tick"] = ts
    runner["ticks"] = int(runner.get("ticks", 0)) + 1
    save_json(RUNNER_STATE_FILE, runner)
    payload = {"time": ts, "changed": changed, "side_effects": side_effects, "ticks": runner["ticks"]}
    print(json.dumps(payload, ensure_ascii=False, indent=2) if verbose else json.dumps(changed, ensure_ascii=False))


def daemon_loop(interval, max_ticks, verbose=False, notify_min_interval=1800, max_active=3):
    ticks = 0
    while True:
        tick_once(verbose=verbose, notify_min_interval=notify_min_interval, max_active=max_active)
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
    tick.add_argument("--max-active", type=int, default=3)
    daemon = sub.add_parser("daemon")
    daemon.add_argument("--interval", type=int, default=60)
    daemon.add_argument("--max-ticks", type=int, default=0)
    daemon.add_argument("--verbose", action="store_true")
    daemon.add_argument("--notify-min-interval", type=int, default=1800)
    daemon.add_argument("--max-active", type=int, default=3)
    args = parser.parse_args()
    if args.command == "tick":
        tick_once(verbose=args.verbose, notify_min_interval=args.notify_min_interval, max_active=args.max_active)
    else:
        daemon_loop(args.interval, args.max_ticks, verbose=args.verbose, notify_min_interval=args.notify_min_interval, max_active=args.max_active)


if __name__ == "__main__":
    main()
