#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from studio_common import NON_RESUMABLE_STATUSES, find_task, load_tasks

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE_PY = os.path.join(BASE_DIR, 'scripts', 'studio_service.py')
NOTION_SYNC_PY = os.path.join(BASE_DIR, 'scripts', 'studio_notion_project.py')
STATUS_TRACE_PY = os.path.join(BASE_DIR, 'scripts', 'studio_status_trace.py')
PROGRESS_ORDERS = {
    'doc': ['intake', 'review_collect', 'review_merge', 'revise', 'polish', 'final_check', 'report', 'done'],
    'code': ['intake', 'plan', 'implement', 'review', 'test', 'fixup', 'report', 'done'],
    'engineering': ['intake', 'investigate', 'execute', 'verify', 'iterate', 'report', 'done'],
    'general': ['intake', 'execute', 'verify', 'report', 'done'],
}


def run_py(script, *args, timeout=45):
    return subprocess.run(
        [sys.executable, script, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def service_status():
    try:
        res = run_py(SERVICE_PY, 'status', timeout=20)
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception:
        pass
    return {}


def parse_ts(value):
    if not value:
        return 0.0
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def inferred_progress(task):
    task_kind = 'doc_review_only' if task.get('type') == 'doc' and task.get('mode') == 'review_only' else (task.get('type') or 'general')
    order = PROGRESS_ORDERS.get(task_kind, PROGRESS_ORDERS['general'])
    phase = task.get('phase')
    try:
        idx = order.index(phase)
    except ValueError:
        idx = 0
    return int(((idx + 1) / len(order)) * 100)


def refresh_task_safe(task_id):
    try:
        run_py(NOTION_SYNC_PY, 'pull', task_id, timeout=45)
    except Exception:
        pass
    try:
        run_py(STATUS_TRACE_PY, task_id, timeout=20)
    except Exception:
        pass


def task_matches(task, task_id=None, match=None):
    if task_id and task.get('id') != task_id:
        return False
    if not match:
        return True
    needle = match.lower()
    hay = ' '.join([
        str(task.get('id') or ''),
        str(task.get('title') or ''),
        str((task.get('project') or {}).get('name') or ''),
        str(task.get('goal') or ''),
    ]).lower()
    return needle in hay


def iter_tasks(data, include_done=False, task_id=None, match=None):
    tasks = []
    for task in data.get('tasks', []):
        if not include_done and task.get('status') in NON_RESUMABLE_STATUSES:
            continue
        if task_matches(task, task_id=task_id, match=match):
            tasks.append(task)
    tasks.sort(key=lambda item: parse_ts(item.get('updated_at')), reverse=True)
    return tasks


def latest_event(task):
    events = ((task.get('notify_state') or {}).get('events') or [])
    if not events:
        return None
    return sorted(events, key=lambda item: parse_ts(item.get('created_at')))[-1]


def summarize_dispatches(task):
    dispatches = task.get('dispatch_plan') or []
    if not dispatches:
        return None
    buckets = {}
    for item in dispatches:
        status = item.get('status') or 'unknown'
        label = f"{item.get('role')}/{item.get('agent')}"
        buckets.setdefault(status, []).append(label)
    parts = []
    for status in ('running', 'planned', 'failed', 'done'):
        labels = buckets.get(status) or []
        if labels:
            parts.append(f"{status}=" + ', '.join(labels[:3]))
    for status, labels in buckets.items():
        if status in {'running', 'planned', 'failed', 'done'}:
            continue
        parts.append(f"{status}=" + ', '.join(labels[:3]))
    return ' | '.join(parts) if parts else None


def summarize_roles(task):
    roles = task.get('active_roles') or []
    if not roles:
        return None
    return ', '.join(f"{item.get('role')}:{item.get('agent')}" for item in roles)


def format_task(task):
    notion = (task.get('notion') or {}).get('last_snapshot') or {}
    event = latest_event(task)
    pending_count = len([e for e in ((task.get('notify_state') or {}).get('events') or []) if not e.get('sent_at')])

    lines = [
        f"[{task.get('id')}] {(task.get('project') or {}).get('name') or task.get('title')}",
        f"type={task.get('type')} phase={task.get('phase')} status={task.get('status')} progress={inferred_progress(task)}%",
    ]
    if notion.get('found'):
        status = notion.get('状态') or '-'
        lines.append(f"notion_status={status}")
        if notion.get('当前负责人'):
            lines.append(f"owner={notion.get('当前负责人')}")
        if notion.get('等待对象'):
            lines.append(f"waiting_on={notion.get('等待对象')}")
        if notion.get('完成证据'):
            lines.append(f"completion={notion.get('完成证据')}")
    roles = summarize_roles(task)
    if roles:
        lines.append(f"roles={roles}")
    dispatches = summarize_dispatches(task)
    if dispatches:
        lines.append(f"dispatch={dispatches}")
    if event:
        lines.append(f"latest={event.get('title')} @ {event.get('created_at')}")
    if pending_count:
        lines.append(f"pending_notify={pending_count}")
    if task.get('next'):
        lines.append(f"next={task.get('next')}")
    if task.get('blocker'):
        lines.append(f"blocker={task.get('blocker')}")
    if (task.get('reporting') or {}).get('next_report_at'):
        lines.append(f"next_report={(task.get('reporting') or {}).get('next_report_at')}")
    if (task.get('reporting') or {}).get('last_report_at'):
        lines.append(f"last_report={(task.get('reporting') or {}).get('last_report_at')}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='show current studio runner progress from real task state')
    parser.add_argument('--task-id')
    parser.add_argument('--match')
    parser.add_argument('--limit', type=int, default=6)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    data = load_tasks()
    tasks = iter_tasks(data, include_done=args.all, task_id=args.task_id, match=args.match)
    if args.refresh:
        for task in tasks[: args.limit]:
            refresh_task_safe(task.get('id'))
        data = load_tasks()
        tasks = iter_tasks(data, include_done=args.all, task_id=args.task_id, match=args.match)

    tasks = tasks[: args.limit]
    service = service_status()

    payload = {
        'service': {
            'bootstrapped': service.get('bootstrapped'),
            'last_tick': ((service.get('runner_state') or {}).get('last_tick')),
            'ticks': ((service.get('runner_state') or {}).get('ticks')),
        },
        'active_count': len(tasks),
        'tasks': [
            {
                'id': task.get('id'),
                'title': task.get('title'),
                'project': (task.get('project') or {}).get('name'),
                'type': task.get('type'),
                'phase': task.get('phase'),
                'status': task.get('status'),
                'progress': inferred_progress(task),
                'next': task.get('next'),
                'blocker': task.get('blocker'),
                'latest_event': latest_event(task),
                'dispatch_summary': summarize_dispatches(task),
                'roles': summarize_roles(task),
            }
            for task in tasks
        ],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    lines = [
        '工作室后台进度',
        f"service={'running' if service.get('bootstrapped') else 'stopped'} last_tick={((service.get('runner_state') or {}).get('last_tick') or '-')}",
        f"active_tasks={len(tasks)}",
    ]
    if not tasks:
        lines.append('当前没有活跃任务。')
    else:
        for task in tasks:
            lines.append('')
            lines.append(format_task(task))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
