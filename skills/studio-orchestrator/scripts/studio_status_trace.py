#!/usr/bin/env python3
import argparse
import json
import os
from typing import Dict, List

from studio_common import ensure_project, ensure_studio_metadata, find_task, load_tasks, now_iso, save_tasks, sync_execution_artifacts, task_state_lock


def role_lines(task: Dict) -> List[str]:
    lines = []
    for item in task.get('agent_plan') or []:
        lines.append(f"- {item.get('role')}: {item.get('agent')} | {item.get('responsibility')}")
    return lines or ['- none']


def artifact_lines(task: Dict) -> List[str]:
    paths = sync_execution_artifacts(task)
    return [f'- {path}' for path in paths] or ['- none']


def latest_logs(task: Dict, limit: int = 12) -> List[str]:
    items = task.get('logs') or []
    tail = items[-limit:]
    return [f"- {item.get('time')} | {item.get('message')}" for item in tail] or ['- none']


def pending_event_lines(task: Dict, limit: int = 8) -> List[str]:
    pending = [event for event in ((task.get('notify_state') or {}).get('events') or []) if not event.get('sent_at')]
    tail = pending[-limit:]
    return [f"- {event.get('created_at')} | {event.get('kind')} | {event.get('title')}" for event in tail] or ['- none']


def notion_line(task: Dict) -> str:
    notion = task.get('notion') or {}
    if notion.get('url'):
        return notion['url']
    return '-'


def notion_snapshot_lines(task: Dict) -> List[str]:
    snap = ((task.get('notion') or {}).get('last_snapshot') or {})
    if not snap.get('found'):
        return ['- none']
    return [
        f"- 项目: {snap.get('项目') or '-'}",
        f"- 任务ID: {snap.get('任务ID') or '-'}",
        f"- 状态: {snap.get('状态') or '-'}",
        f"- 优先级: {snap.get('优先级') or '-'}",
        f"- 阶段细节: {snap.get('阶段细节') or '-'}",
        f"- 当前负责人: {snap.get('当前负责人') or '-'}",
        f"- 等待对象: {snap.get('等待对象') or '-'}",
        f"- 交付物: {snap.get('交付物') or '-'}",
        f"- 风险: {snap.get('风险') or '-'}",
        f"- 备注: {snap.get('备注') or '-'}",
        f"- 完成证据: {snap.get('完成证据') or '-'}",
        f"- 替代关系: {snap.get('替代关系') or '-'}",
        f"- 系统来源: {snap.get('系统来源') or '-'}",
        f"- 同步诊断: {snap.get('同步诊断') or '-'}",
        f"- 下一次汇报: {snap.get('下一次汇报') or '-'}",
    ]


def render(task: Dict) -> str:
    ensure_studio_metadata(task)
    project = ensure_project(task)
    reporting = task.get('reporting') or {}
    task_scope = task.get('task_scope') or 'execution_run'
    lines = [
        f"# {project['name']}",
        '',
        '## 概览',
        f"- 任务ID: {task.get('id')}",
        f"- 标题: {task.get('title')}",
        f"- 类型: {task.get('type')}",
        f"- 任务层级: {task_scope}",
        f"- 上级任务: {task.get('parent_task_id') or '-'}",
        f"- 下级任务: {', '.join(task.get('child_task_ids') or []) or '-'}",
        f"- 目标: {task.get('goal')}",
        f"- 阶段: {task.get('phase')} | 状态: {task.get('status')}",
        f"- 下一步: {task.get('next') or '-'}",
        f"- 阻塞: {task.get('blocker') or '-'}",
        f"- 下次汇报: {reporting.get('next_report_at') or '-'}",
        f"- 上次汇报: {reporting.get('last_report_at') or '-'}",
        f"- Notion: {notion_line(task)}",
        '',
        '## Notion 快照',
        *notion_snapshot_lines(task),
        '',
        '## 角色分工',
        *role_lines(task),
        '',
        '## 已绑定产物',
        *artifact_lines(task),
        '',
        '## 最近日志',
        *latest_logs(task),
        '',
        '## 待发送里程碑',
        *pending_event_lines(task),
        '',
    ]
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description='write local studio status trace for a task')
    parser.add_argument('task_id')
    args = parser.parse_args()

    with task_state_lock():
        data = load_tasks()
        task = find_task(data, args.task_id)
        if not task:
            raise SystemExit(f'task not found: {args.task_id}')

        ensure_studio_metadata(task)
        trace = task.get('status_trace') or {}
        path = trace.get('path')
        if not path:
            raise SystemExit('status trace path missing')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(render(task).rstrip() + '\n')
        task['status_trace']['last_sync_at'] = now_iso()
        task['updated_at'] = now_iso()
        save_tasks(data)
    print(json.dumps({'task_id': task.get('id'), 'status_trace': task.get('status_trace')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
