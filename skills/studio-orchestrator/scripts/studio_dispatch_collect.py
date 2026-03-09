#!/usr/bin/env python3
import argparse
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, 'state', 'tasks.json')

DONE_MARKERS = ['answer:', '审稿意见', '结论先说', '## ', 'good', '完成', 'done']
FAIL_MARKERS = ['error', 'failed', 'traceback', 'enoent']


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


def classify(text):
    low = text.lower()
    if any(m in low for m in FAIL_MARKERS):
        return 'failed'
    if any(m in low for m in DONE_MARKERS):
        return 'done'
    return 'running'


def main():
    parser = argparse.ArgumentParser(description='collect wrapper output and update dispatch item status')
    parser.add_argument('task_id')
    parser.add_argument('dispatch_id')
    parser.add_argument('output_path')
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f'task not found: {args.task_id}')

    text = ''
    if os.path.exists(args.output_path):
        with open(args.output_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()

    status = classify(text)
    changed = None
    for coll in ['dispatch_plan', 'dispatch_history']:
        for item in task.get(coll, []) or []:
            if item.get('id') == args.dispatch_id:
                item['status'] = status
                item['output_path'] = args.output_path
                changed = item
    task.setdefault('logs', []).append({'time': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).astimezone().isoformat(timespec='seconds'), 'message': f'dispatch collect: {args.dispatch_id} => {status}'})
    save_tasks(data)
    print(json.dumps({'task_id': args.task_id, 'dispatch_id': args.dispatch_id, 'status': status, 'output_path': args.output_path}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
