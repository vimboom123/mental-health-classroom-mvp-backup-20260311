#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, 'state', 'tasks.json')


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {'tasks': []}
    with open(TASKS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_tasks(data):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def find_task(data, task_id):
    for t in data.get('tasks', []):
        if t.get('id') == task_id:
            return t
    return None


def main():
    parser = argparse.ArgumentParser(description='mark substantive completion evidence for a task')
    parser.add_argument('task_id')
    parser.add_argument('--kind', required=True, choices=['doc', 'code', 'engineering', 'general'])
    parser.add_argument('--summary', required=True)
    parser.add_argument('--review-merged', action='store_true')
    parser.add_argument('--artifact-validated', action='store_true')
    parser.add_argument('--main-acceptance', action='store_true')
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f'task not found: {args.task_id}')

    task['completion_evidence'] = {
        'kind': args.kind,
        'review_merged': bool(args.review_merged),
        'artifact_validated': bool(args.artifact_validated),
        'main_acceptance': bool(args.main_acceptance),
        'summary': args.summary,
        'marked_at': now_iso(),
        'marked_by': 'main-agent',
    }
    task.setdefault('logs', []).append({'time': now_iso(), 'message': f'completion evidence marked: {args.summary}'})
    save_tasks(data)
    print(json.dumps({'task_id': task['id'], 'completion_evidence': task['completion_evidence']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
