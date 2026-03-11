#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from typing import Optional

from studio_common import (
    add_event,
    ensure_execution,
    ensure_notify,
    ensure_notify_state,
    ensure_project,
    ensure_reporting,
    ensure_studio_metadata,
    find_resume_candidate,
    find_task,
    load_tasks,
    normalize_path,
    normalize_paths,
    now_iso,
    save_tasks,
    seed_artifact_state,
    sync_execution_artifacts,
    task_state_lock,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK_PY = os.path.join(BASE_DIR, 'scripts', 'studio_task.py')
RUNNER_PY = os.path.join(BASE_DIR, 'scripts', 'studio_runner.py')
SERVICE_PY = os.path.join(BASE_DIR, 'scripts', 'studio_service.py')
ROLES_PY = os.path.join(BASE_DIR, 'scripts', 'studio_roles.py')
ACTIVE_ROLES_PY = os.path.join(BASE_DIR, 'scripts', 'studio_active_roles.py')
NEXT_ACTIONS_PY = os.path.join(BASE_DIR, 'scripts', 'studio_next_actions.py')
DISPATCH_PLAN_PY = os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_plan.py')
NOTION_SYNC_PY = os.path.join(BASE_DIR, 'scripts', 'studio_notion_project.py')
STATUS_TRACE_PY = os.path.join(BASE_DIR, 'scripts', 'studio_status_trace.py')
NOTIFY_PY = os.path.join(BASE_DIR, 'scripts', 'studio_notify.py')


def call(script, *args, check=True):
    return subprocess.run([sys.executable, script, *args], check=check, capture_output=True, text=True)


def normalize_quality_mode(value):
    raw = (value or '').strip().lower()
    if raw in {'quality_first', 'quality-first', 'high', 'highest'}:
        return 'strict'
    if raw in {'default', 'normal'}:
        return 'balanced'
    if raw in {'fast', 'performance'}:
        return 'speed'
    return raw or None


EXECUTION_RUN_HINTS = (
    'execution run',
    'execution_run',
    'execution-run',
    'restart',
    'rerun',
    '重新拉起',
    '重新启动',
    '重新开始',
    'follow-up',
    'follow up',
)
PROJECT_BASE_HINTS = (
    '持续推进',
    '项目底座',
    'project base',
    '长期跟踪',
)
PROJECT_BASE_NAME_HINTS = ('planning', 'project', '项目')


def has_any_hint(text, hints):
    haystack = (text or '').strip().lower()
    return any(hint in haystack for hint in hints)


def delivery_standard(task_type: str) -> str:
    if task_type == 'doc':
        return '真实文档改动、review 汇总、final_check、完成汇报'
    if task_type == 'code':
        return '真实代码改动、review、测试/修正、完成汇报'
    if task_type == 'engineering':
        return '真实执行结果、验证结论、风险记录、完成汇报'
    return '真实产物、状态留痕、阶段汇报、完成结论'


def role_summary(task) -> str:
    parts = []
    for item in task.get('agent_plan') or []:
        agent = item.get('agent')
        role = item.get('role')
        parts.append(f"{agent}:{role}")
    return ' | '.join(parts) if parts else 'main-agent'


def append_kickoff_event(task_id: str, *, resumed: bool = False) -> None:
    with task_state_lock():
        data = load_tasks()
        task = find_task(data, task_id)
        if not task:
            raise SystemExit(f'task not found: {task_id}')
        project = ensure_project(task)
        reporting = ensure_reporting(task)
        add_event(
            task,
            key=f"{task_id}:{'resume' if resumed else 'kickoff'}",
            kind='resume' if resumed else 'kickoff',
            title='工作室继续推进' if resumed else '工作室已开工',
            detail_lines=[
                f"project={project['name']}",
                f"goal={task.get('goal')}",
                f"roles={role_summary(task)}",
                f"delivery={delivery_standard(task.get('type') or 'general')}",
                f"next_report={reporting.get('next_report_at') or '-'}",
            ],
        )
        task.setdefault('logs', []).append({'time': now_iso(), 'message': 'studio resumed from previous record' if resumed else 'studio kickoff announced'})
        task['updated_at'] = now_iso()
        save_tasks(data)


def ensure_project_traces(task_id: str, *, force_notion: bool = True) -> None:
    pull = call(NOTION_SYNC_PY, 'pull', task_id, check=False)
    if pull.returncode != 0:
        raise SystemExit(pull.stderr.strip() or pull.stdout.strip() or 'notion pull failed')
    notion_args = ['sync', task_id]
    if force_notion:
        notion_args.append('--force')
    else:
        notion_args.extend(['--min-interval', '300'])
    notion = call(NOTION_SYNC_PY, *notion_args, check=False)
    if notion.returncode != 0:
        call(TASK_PY, 'update', task_id, '--status', 'blocked', '--blocker', f'notion sync failed: {(notion.stderr or notion.stdout).strip()[:300]}', '--next', '修复 Notion 底座后重试', '--log', 'studio_start: notion sync failed', check=False)
        raise SystemExit(notion.stderr.strip() or notion.stdout.strip() or 'notion sync failed')
    trace = call(STATUS_TRACE_PY, task_id, check=True)
    call(TASK_PY, 'log', task_id, 'studio_start: notion base and local status trace synced', check=False)


def resume_task_if_exists(args: argparse.Namespace, *, preferred_scope: Optional[str] = None) -> str:
    artifacts = normalize_paths((args.artifact or []) + ([args.doc_path] if args.doc_path else []))
    workdir = normalize_path(args.workdir)
    incoming_quality_mode = normalize_quality_mode(getattr(args, 'quality_mode', None))
    incoming_quality_priority = (getattr(args, 'quality_priority', None) or '').strip() or None
    with task_state_lock():
        data = load_tasks()
        task = find_resume_candidate(
            data,
            task_id=getattr(args, 'task_id', None),
            title=args.title,
            project_name=args.project_name or args.title,
            workdir=workdir,
            artifacts=artifacts,
            preferred_scope=preferred_scope,
        )
        if not task:
            return ''

        ensure_studio_metadata(task)
        if (task.get('task_scope') or 'execution_run') != 'project_base':
            task['title'] = args.title
            task['goal'] = args.goal
        project = ensure_project(task)
        project['name'] = args.project_name or project.get('name') or args.title
        execution = ensure_execution(task)
        if workdir:
            execution['workdir'] = workdir
        if artifacts:
            merged = normalize_paths((task.get('artifacts') or []) + artifacts)
            task['artifacts'] = merged
            execution['artifacts'] = merged
        if args.watch_file:
            task['watched_files'] = normalize_paths((task.get('watched_files') or []) + (args.watch_file or []))
        if args.watch_process_log:
            task['watched_process_logs'] = normalize_paths((task.get('watched_process_logs') or []) + (args.watch_process_log or []))
        if args.notify_target:
            task['notify'] = {
                'channel': args.notify_channel,
                'target': args.notify_target,
                'policy': args.notify_policy,
            }
        if incoming_quality_mode:
            task['quality_mode'] = incoming_quality_mode
        elif not task.get('quality_mode'):
            task['quality_mode'] = 'strict'
        if incoming_quality_priority is not None:
            task['quality_priority'] = incoming_quality_priority
        elif not str(task.get('quality_priority') or '').strip():
            task['quality_priority'] = 'quality' if task.get('quality_mode') == 'strict' else task.get('quality_mode')
        ensure_notify(task)
        ensure_notify_state(task)
        sync_execution_artifacts(task)
        seed_artifact_state(task)
        if task.get('status') in {'blocked', 'waiting_user', 'failed'}:
            task['status'] = 'in_progress'
            task['blocker'] = None
        task['next'] = '继续沿用既有记录推进工作室任务'
        task.setdefault('runtime', {})['mode'] = 'studio-service'
        task['updated_at'] = now_iso()
        save_tasks(data)
        return task['id']
    return ''


def infer_task_scope(args: argparse.Namespace) -> str:
    explicit = getattr(args, 'task_scope', None)
    if explicit:
        return explicit
    title = (args.title or '').strip()
    goal = (args.goal or '').strip()
    combined = '\n'.join(part for part in [title, goal] if part)
    if has_any_hint(combined, EXECUTION_RUN_HINTS):
        return 'execution_run'
    if has_any_hint(combined, PROJECT_BASE_HINTS):
        return 'project_base'
    projectish = (args.project_name or args.title or '').strip().lower()
    if any(key in projectish for key in PROJECT_BASE_NAME_HINTS):
        return 'project_base'
    return 'execution_run'


def infer_parent_task_id(args: argparse.Namespace, *, task_scope: str) -> str:
    explicit = (getattr(args, 'parent_task_id', None) or '').strip()
    if explicit:
        return explicit
    if task_scope != 'execution_run':
        return ''
    artifacts = normalize_paths((args.artifact or []) + ([args.doc_path] if args.doc_path else []))
    workdir = normalize_path(args.workdir)
    with task_state_lock():
        data = load_tasks()
        parent = find_resume_candidate(
            data,
            project_name=args.project_name or args.title,
            workdir=workdir,
            artifacts=artifacts,
            preferred_scope='project_base',
        )
        return parent.get('id') if parent else ''


def main():
    parser = argparse.ArgumentParser(description='create a studio task and ensure persistent runner service')
    parser.add_argument('--task-id')
    parser.add_argument('title')
    parser.add_argument('type', choices=['doc', 'code', 'engineering', 'general'])
    parser.add_argument('goal')
    parser.add_argument('--project-name')
    parser.add_argument('--task-scope', choices=['execution_run', 'project_base'])
    parser.add_argument('--parent-task-id')
    parser.add_argument('--artifact', action='append')
    parser.add_argument('--doc-path')
    parser.add_argument('--workdir')
    parser.add_argument('--watch-file', action='append')
    parser.add_argument('--watch-process-log', action='append')
    parser.add_argument('--notify-target')
    parser.add_argument('--notify-channel', default='telegram')
    parser.add_argument('--notify-policy', default='milestones')
    parser.add_argument('--quality-mode')
    parser.add_argument('--quality-priority')
    parser.add_argument('--execution-mode', choices=['serial', 'parallel'], default='serial')
    parser.add_argument('--serial-queue-json')
    parser.add_argument('--agent-plan-json')
    parser.add_argument('--background', dest='background', action='store_true', default=True)
    parser.add_argument('--foreground', dest='background', action='store_false')
    args = parser.parse_args()

    inferred_scope = infer_task_scope(args)
    resumed = False
    task_id = resume_task_if_exists(args, preferred_scope=inferred_scope)
    if task_id:
        resumed = True
        call(TASK_PY, 'log', task_id, 'studio_start: resumed existing task record', check=False)
    else:
        parent_task_id = infer_parent_task_id(args, task_scope=inferred_scope)
        cmd = [
            sys.executable, TASK_PY, 'create',
            '--title', args.title,
            '--type', args.type,
            '--task-scope', inferred_scope,
            '--goal', args.goal,
            '--status', 'in_progress',
            '--phase', 'intake',
            '--next', '工作室接管任务，已进入开工与拆工阶段',
            '--owner', 'main-agent',
            '--log', 'studio_start: task created and handed to studio service',
        ]
        quality_mode = normalize_quality_mode(args.quality_mode) or 'strict'
        quality_priority = (args.quality_priority or '').strip() or ('quality' if quality_mode == 'strict' else quality_mode)
        cmd.extend(['--quality-mode', quality_mode, '--quality-priority', quality_priority])
        if args.project_name:
            cmd.extend(['--project-name', args.project_name])
        if parent_task_id:
            cmd.extend(['--parent-task-id', parent_task_id])
        for path in args.artifact or []:
            cmd.extend(['--artifact', path])
        if args.doc_path:
            cmd.extend(['--doc-path', args.doc_path])
        if args.workdir:
            cmd.extend(['--workdir', args.workdir])
        for path in args.watch_file or []:
            cmd.extend(['--watch-file', path])
        for path in args.watch_process_log or []:
            cmd.extend(['--watch-process-log', path])
        if args.notify_target:
            cmd.extend([
                '--notify-target', args.notify_target,
                '--notify-channel', args.notify_channel,
                '--notify-policy', args.notify_policy,
            ])
        task_id = subprocess.check_output(cmd, text=True).strip()

    with task_state_lock():
        data = load_tasks()
        task = find_task(data, task_id)
        if task:
            task['execution_mode'] = args.execution_mode or 'serial'
            if args.agent_plan_json:
                try:
                    task['agent_plan'] = json.loads(args.agent_plan_json)
                    task['lock_agent_plan'] = True
                except Exception as exc:
                    raise SystemExit(f'agent-plan-json parse failed: {exc}')
            if args.serial_queue_json:
                try:
                    queue = json.loads(args.serial_queue_json)
                    task['serial_queue'] = queue
                    task['current_serial_index'] = 0
                    if (task.get('execution_mode') or 'serial') == 'serial' and queue:
                        task['active_roles'] = [queue[0]]
                        task['next_actions'] = [
                            {
                                'role': queue[0].get('role'),
                                'agent': queue[0].get('agent'),
                                'action': queue[0].get('action'),
                                'required': queue[0].get('required'),
                            }
                        ]
                except Exception as exc:
                    raise SystemExit(f'serial-queue-json parse failed: {exc}')
            task['updated_at'] = now_iso()
            save_tasks(data)

    with task_state_lock():
        data = load_tasks()
        task = find_task(data, task_id)
        use_custom_serial = bool(task and ((task.get('execution_mode') == 'serial' and task.get('serial_queue')) or task.get('lock_agent_plan')))

    if use_custom_serial:
        for script in (ACTIVE_ROLES_PY, NEXT_ACTIONS_PY, DISPATCH_PLAN_PY):
            subprocess.run([sys.executable, script, task_id], check=True)
    else:
        for script in (ROLES_PY, ACTIVE_ROLES_PY, NEXT_ACTIONS_PY, DISPATCH_PLAN_PY):
            subprocess.run([sys.executable, script, task_id], check=True)

    append_kickoff_event(task_id, resumed=resumed)
    call(NOTIFY_PY, '--task-id', task_id, check=False)
    ensure_project_traces(task_id, force_notion=True)

    if args.background:
        subprocess.run([sys.executable, SERVICE_PY, 'ensure', '--interval', '30'], check=True)
    else:
        subprocess.run(
            [
                sys.executable,
                RUNNER_PY,
                'tick',
                '--verbose',
                '--lock-retries',
                '8',
                '--lock-retry-delay-ms',
                '250',
            ],
            check=True,
        )

    print(f'TASK_ID={task_id}')


if __name__ == '__main__':
    main()
