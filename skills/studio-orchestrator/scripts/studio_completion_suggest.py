#!/usr/bin/env python3
import argparse
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, 'state', 'tasks.json')


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


def suggest(task):
    dispatch = task.get('dispatch_history') or task.get('dispatch_plan') or []
    logs = '\n'.join(x.get('message', '') for x in task.get('logs', []))
    artifacts = task.get('artifacts') or []
    completion = task.setdefault('completion_evidence', {})

    review_done = any(x.get('status') == 'done' for x in dispatch if x.get('kind') in {'review', 'second-opinion', 'cn-review'})
    artifact_validated = bool(artifacts)

    completion.setdefault('kind', task.get('type') or 'general')
    completion['review_merged'] = bool(review_done)
    completion['artifact_validated'] = bool(artifact_validated)
    completion.setdefault('main_acceptance', False)
    completion.setdefault('summary', '')
    return completion


def main():
    parser = argparse.ArgumentParser(description='auto-suggest completion evidence fields from task state')
    parser.add_argument('task_id')
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f'task not found: {args.task_id}')
    completion = suggest(task)
    save_tasks(data)
    print(json.dumps({'task_id': task['id'], 'completion_evidence': completion}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
