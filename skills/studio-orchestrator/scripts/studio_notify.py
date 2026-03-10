#!/usr/bin/env python3
import argparse
import json
import subprocess

from studio_common import find_task, load_tasks, mark_events_sent, pending_events, save_tasks, task_state_lock

OPENCLAW_BIN = '/Users/vimboom/.npm-global/bin/openclaw'
MAX_MESSAGE_CHARS = 3500


def summarize_event(event):
    lines = [line.strip() for line in (event.get('text') or '').splitlines()[2:] if line.strip()]
    detail = ' | '.join(lines[:3])
    if detail:
        return f"- {event.get('title')}: {detail}"
    return f"- {event.get('title')}"


def build_task_message(task, events):
    project = (task.get('project') or {}).get('name') or task.get('title')
    notion = (task.get('notion') or {}).get('url')
    next_report = (task.get('reporting') or {}).get('next_report_at')
    lines = [
        f"[{task.get('id')}] {project}",
        f"title={task.get('title')}",
        f"phase={task.get('phase')} status={task.get('status')}",
        '新增进展:',
    ]
    for event in events:
        lines.append(summarize_event(event))
    next_step = task.get('next')
    blocker = task.get('blocker')
    if next_step:
        lines.append(f"next={next_step}")
    if blocker:
        lines.append(f"blocker={blocker}")
    if next_report:
        lines.append(f"next_report={next_report}")
    if notion:
        lines.append(f"notion={notion}")
    message = '\n'.join(lines)
    if len(message) <= MAX_MESSAGE_CHARS:
        return message
    trimmed = []
    current = lines[:3]
    for event in events:
        line = summarize_event(event)
        probe = '\n'.join(current + [line, f"... 其余 {len(events) - len(trimmed) - 1} 条进展已省略", f"next={next_step}" if next_step else ''])
        if len(probe) > MAX_MESSAGE_CHARS:
            break
        trimmed.append(line)
        current.append(line)
    if len(trimmed) < len(events):
        current.append(f"... 其余 {len(events) - len(trimmed)} 条进展已省略")
    if next_step:
        current.append(f"next={next_step}")
    if blocker:
        current.append(f"blocker={blocker}")
    return '\n'.join(current)


def main():
    parser = argparse.ArgumentParser(description='send pending studio milestone events via OpenClaw messaging')
    parser.add_argument('--task-id')
    parser.add_argument('--target')
    parser.add_argument('--channel')
    parser.add_argument('--min-interval', type=int, default=0)
    args = parser.parse_args()

    with task_state_lock():
        data = load_tasks()
        tasks = data.get('tasks', [])
        if args.task_id:
            task = find_task(data, args.task_id)
            tasks = [task] if task else []

        sent = 0
        sent_tasks = 0
        for task in tasks:
            if not task:
                continue
            notify = task.get('notify') or {}
            channel = args.channel or notify.get('channel') or 'telegram'
            target = args.target or notify.get('target')
            if not target:
                task.setdefault('logs', []).append({'time': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).astimezone().isoformat(timespec='seconds'), 'message': 'notify skipped: missing target'})
                continue
            events = pending_events(task)
            if not events:
                continue
            event_keys = [event.get('key') for event in events if event.get('key')]
            message = build_task_message(task, events)
            try:
                subprocess.run([
                    OPENCLAW_BIN,
                    'message', 'send',
                    '--channel', channel,
                    '--target', str(target),
                    '--message', message,
                ], check=True, timeout=25)
                task.setdefault('logs', []).append({'time': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).astimezone().isoformat(timespec='seconds'), 'message': f'notify sent: {len(event_keys)} events via {channel} to {target}'})
            except Exception as exc:
                task.setdefault('logs', []).append({'time': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).astimezone().isoformat(timespec='seconds'), 'message': f'notify failed: {channel}/{target} {exc}'})
                continue
            if event_keys:
                mark_events_sent(task, [key for key in event_keys if key])
                sent += len(event_keys)
                sent_tasks += 1
        save_tasks(data)
    print(json.dumps({'sent_events': sent, 'sent_tasks': sent_tasks}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
