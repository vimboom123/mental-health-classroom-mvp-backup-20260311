#!/usr/bin/env python3
import argparse
import json
import sys
import uuid
from typing import Any, Dict, Optional

from studio_common import (
    add_event,
    ensure_execution,
    ensure_notify,
    ensure_notify_state,
    ensure_project,
    ensure_studio_metadata,
    load_tasks,
    normalize_path,
    normalize_paths,
    now_iso,
    resolve_default_notify,
    save_tasks,
    seed_artifact_state,
    slugify,
    sync_execution_artifacts,
    task_state_lock,
    find_task,
)

VALID_STATUS = {
    "queued",
    "in_progress",
    "waiting_reviewer",
    "waiting_user",
    "blocked",
    "done",
    "failed",
    "cancelled",
}


def base_progress(percent: int, current: int, total: int, status_text: str) -> Dict[str, Any]:
    return {
        "percent": percent,
        "current": current,
        "total": total,
        "status_text": status_text,
        "last_feedback_ts": None,
    }


def validate_create_args(args: argparse.Namespace) -> None:
    artifacts = normalize_paths((args.artifact or []) + ([args.doc_path] if args.doc_path else []))
    if args.type == "doc" and not artifacts:
        sys.exit("doc tasks require --artifact or --doc-path")
    if args.type == "code" and not args.workdir:
        sys.exit("code tasks require --workdir")


def build_notify(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    if args.notify_target:
        return {
            "channel": args.notify_channel,
            "target": args.notify_target,
            "policy": args.notify_policy,
        }
    return resolve_default_notify()


def maybe_log(task: Dict[str, Any], message: Optional[str], *, ts: Optional[str] = None) -> None:
    if not message:
        return
    task.setdefault("logs", []).append({"time": ts or now_iso(), "message": message})


def cmd_create(args: argparse.Namespace) -> None:
    validate_create_args(args)
    with task_state_lock():
        data = load_tasks()
        task_id = uuid.uuid4().hex[:8]
        ts = now_iso()
        artifacts = normalize_paths((args.artifact or []) + ([args.doc_path] if args.doc_path else []))
        workdir = normalize_path(args.workdir)
        notify = build_notify(args)
        task = {
            "id": task_id,
            "title": args.title,
            "type": args.type,
            "goal": args.goal,
            "status": args.status,
            "phase": args.phase,
            "next": args.next_step,
            "owner": args.owner,
            "mode": args.mode,
            "artifacts": artifacts,
            "watched_files": normalize_paths(args.watch_file or []),
            "watched_process_logs": normalize_paths(args.watch_process_log or []),
            "notify": notify,
            "priority": args.priority,
            "progress": base_progress(
                args.progress_percent,
                args.progress_current,
                args.progress_total,
                args.progress_status,
            ),
            "blocker": args.blocker,
            "created_at": ts,
            "updated_at": ts,
            "runtime": {
                "mode": "studio-service",
                "started_by": "studio_task.py",
            },
            "execution": {
                "workdir": workdir,
                "artifacts": artifacts,
                "artifact_state": {},
            },
            "notify_state": {
                "events": [],
                "sent_event_keys": [],
            },
            "logs": [],
        }
        if args.project_name:
            task["project"] = {"name": args.project_name}
        maybe_log(task, args.log or "task created", ts=ts)
        ensure_studio_metadata(task)
        if args.project_name:
            project = ensure_project(task)
            project["name"] = args.project_name
            project["slug"] = slugify(args.project_name, fallback=task_id)
        ensure_execution(task)
        ensure_notify(task)
        ensure_notify_state(task)
        sync_execution_artifacts(task)
        seed_artifact_state(task)
        add_event(
            task,
            key=f"{task_id}:created:{task['phase']}:{task['status']}",
            kind="task-created",
            title="工作室任务已创建",
            detail_lines=[
                f"phase={task['phase']} status={task['status']}",
                f"type={task['type']}",
                f"next={task.get('next') or '-'}",
            ],
        )
        if task.get("blocker"):
            add_event(
                task,
                key=f"{task_id}:blocker:{task['blocker']}",
                kind="blocker",
                title="任务存在阻塞",
                detail_lines=[f"blocker={task['blocker']}", f"next={task.get('next') or '-'}"],
            )
        data.setdefault("tasks", []).append(task)
        save_tasks(data)
    print(task_id)


def cmd_list(args: argparse.Namespace) -> None:
    data = load_tasks()
    tasks = data.get("tasks", [])
    if args.status:
        tasks = [t for t in tasks if t.get("status") == args.status]
    if args.type:
        tasks = [t for t in tasks if t.get("type") == args.type]
    if args.json:
        print(json.dumps(tasks, ensure_ascii=False, indent=2))
        return
    for t in tasks:
        print(f"{t['id']} | {t['status']} | {t['type']} | {t['phase']} | {t['title']}")
        print(f"  next: {t.get('next') or '-'}")
        print(f"  owner: {t.get('owner') or '-'} | updated: {t['updated_at']}")
        if t.get("blocker"):
            print(f"  blocker: {t['blocker']}")


def cmd_show(args: argparse.Namespace) -> None:
    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        sys.exit(f"task not found: {args.task_id}")
    print(json.dumps(task, ensure_ascii=False, indent=2))


def maybe_add_transition_events(task: Dict[str, Any], task_id: str, before: Dict[str, Any]) -> None:
    if before.get("phase") != task.get("phase"):
        add_event(
            task,
            key=f"{task_id}:phase:{task.get('phase')}",
            kind="phase",
            title="阶段推进",
            detail_lines=[
                f"from={before.get('phase') or '-'}",
                f"to={task.get('phase') or '-'}",
                f"next={task.get('next') or '-'}",
            ],
        )
    if before.get("status") != task.get("status"):
        add_event(
            task,
            key=f"{task_id}:status:{task.get('status')}",
            kind="status",
            title="任务状态更新",
            detail_lines=[
                f"from={before.get('status') or '-'}",
                f"to={task.get('status') or '-'}",
                f"next={task.get('next') or '-'}",
            ],
        )
    if before.get("blocker") != task.get("blocker"):
        if task.get("blocker"):
            add_event(
                task,
                key=f"{task_id}:blocker:{task.get('blocker')}",
                kind="blocker",
                title="出现新的阻塞",
                detail_lines=[
                    f"blocker={task.get('blocker')}",
                    f"phase={task.get('phase') or '-'} status={task.get('status') or '-'}",
                    f"next={task.get('next') or '-'}",
                ],
            )
        elif before.get("blocker"):
            add_event(
                task,
                key=f"{task_id}:blocker-cleared:{before.get('blocker')}",
                kind="blocker-cleared",
                title="阻塞已解除",
                detail_lines=[
                    f"cleared={before.get('blocker')}",
                    f"next={task.get('next') or '-'}",
                ],
            )


def cmd_update(args: argparse.Namespace) -> None:
    with task_state_lock():
        data = load_tasks()
        task = find_task(data, args.task_id)
        if not task:
            sys.exit(f"task not found: {args.task_id}")
        before = {
            "status": task.get("status"),
            "phase": task.get("phase"),
            "blocker": task.get("blocker"),
        }
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
        if args.clear_blocker:
            task["blocker"] = None
            changed = True
        ensure_studio_metadata(task)
        if args.project_name:
            project = ensure_project(task)
            project["name"] = args.project_name
            project["slug"] = slugify(args.project_name, fallback=args.task_id)
            changed = True
        execution = ensure_execution(task)
        if args.artifact or args.doc_path:
            merged = normalize_paths((task.get("artifacts") or []) + (args.artifact or []) + ([args.doc_path] if args.doc_path else []))
            task["artifacts"] = merged
            execution["artifacts"] = merged
            changed = True
        if args.workdir is not None:
            execution["workdir"] = normalize_path(args.workdir)
            changed = True
        if args.priority is not None:
            task["priority"] = args.priority
            changed = True
        progress = task.setdefault("progress", {})
        for key, value in [
            ("percent", args.progress_percent),
            ("current", args.progress_current),
            ("total", args.progress_total),
            ("status_text", args.progress_status),
        ]:
            if value is not None:
                progress[key] = value
                changed = True
        if args.notify_target or args.notify_channel or args.notify_policy:
            notify = task.get("notify") or {}
            if args.notify_target:
                notify["target"] = args.notify_target
            if args.notify_channel:
                notify["channel"] = args.notify_channel
            if args.notify_policy:
                notify["policy"] = args.notify_policy
            task["notify"] = notify
            changed = True
        ensure_notify(task)
        ensure_notify_state(task)
        sync_execution_artifacts(task)
        if changed:
            task["updated_at"] = now_iso()
            maybe_log(task, args.log, ts=task["updated_at"])
            seed_artifact_state(task)
            maybe_add_transition_events(task, args.task_id, before)
            save_tasks(data)
    print(json.dumps(task, ensure_ascii=False, indent=2))


def cmd_log(args: argparse.Namespace) -> None:
    with task_state_lock():
        data = load_tasks()
        task = find_task(data, args.task_id)
        if not task:
            sys.exit(f"task not found: {args.task_id}")
        ts = now_iso()
        maybe_log(task, args.message, ts=ts)
        task["updated_at"] = ts
        save_tasks(data)
    print(ts)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="studio orchestrator task registry")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("create")
    c.add_argument("--title", required=True)
    c.add_argument("--project-name")
    c.add_argument("--type", required=True, choices=["doc", "code", "engineering", "general"])
    c.add_argument("--mode", choices=["default", "review_only"], default="default")
    c.add_argument("--goal", required=True)
    c.add_argument("--status", default="queued", choices=sorted(VALID_STATUS))
    c.add_argument("--phase", default="intake")
    c.add_argument("--next", dest="next_step", default="")
    c.add_argument("--owner", default="main-agent")
    c.add_argument("--artifact", action="append")
    c.add_argument("--doc-path")
    c.add_argument("--workdir")
    c.add_argument("--watch-file", action="append")
    c.add_argument("--watch-process-log", action="append")
    c.add_argument("--notify-channel", default="telegram")
    c.add_argument("--notify-target")
    c.add_argument("--notify-policy", default="milestones")
    c.add_argument("--priority", type=int, default=50)
    c.add_argument("--progress-percent", type=int, default=0)
    c.add_argument("--progress-current", type=int, default=0)
    c.add_argument("--progress-total", type=int, default=0)
    c.add_argument("--progress-status", default="")
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
    u.add_argument("--project-name")
    u.add_argument("--next", dest="next_step")
    u.add_argument("--owner")
    u.add_argument("--artifact", action="append")
    u.add_argument("--doc-path")
    u.add_argument("--workdir")
    u.add_argument("--priority", type=int)
    u.add_argument("--progress-percent", type=int)
    u.add_argument("--progress-current", type=int)
    u.add_argument("--progress-total", type=int)
    u.add_argument("--progress-status")
    u.add_argument("--notify-channel")
    u.add_argument("--notify-target")
    u.add_argument("--notify-policy")
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
