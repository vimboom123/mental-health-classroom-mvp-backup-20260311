#!/usr/bin/env python3
import argparse
import json
import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, 'state', 'tasks.json')
COLLECT_PY = os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_collect.py')


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {'tasks': []}
    with open(TASKS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_task(data, task_id):
    for t in data.get('tasks', []):
        if t.get('id') == task_id:
            return t
    return None


def main():
    parser = argparse.ArgumentParser(description='poll launched dispatch meta and collect result when ready')
    parser.add_argument('task_id')
    parser.add_argument('dispatch_id')
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f'task not found: {args.task_id}')
    item = next((x for x in (task.get('dispatch_plan') or []) if x.get('id') == args.dispatch_id), None)
    if not item:
        raise SystemExit(f'dispatch item not found: {args.dispatch_id}')
    meta_path = item.get('runtime_meta')
    if not meta_path or not os.path.exists(meta_path):
        print(json.dumps({'ready': False, 'reason': 'runtime meta missing'}, ensure_ascii=False, indent=2))
        return
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    payload = meta.get('payload') or {}
    output_path = payload.get('output_path')
    if output_path:
        subprocess.run([sys.executable, COLLECT_PY, args.task_id, args.dispatch_id, output_path], check=True)
        print(json.dumps({'ready': True, 'output_path': output_path}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({'ready': False, 'reason': 'no output path yet'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
