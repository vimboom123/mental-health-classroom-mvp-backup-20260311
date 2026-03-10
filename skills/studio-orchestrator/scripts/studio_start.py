#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

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


def resume_task_if_exists(args: argparse.Namespace) -> str:
    artifacts = normalize_paths((args.artifact or []) + ([args.doc_path] if args.doc_path else []))
    workdir = normalize_path(args.workdir)
    with task_state_lock():
        data = load_tasks()
        task = find_resume_candidate(
            data,
            task_id=getattr(args, 'task_id', None),
            title=args.title,
            project_name=args.project_name or args.title,
            workdir=workdir,
            artifacts=artifacts,
        )
        if not task:
            return ''

        task['title'] = args.title
        task['goal'] = args.goal
        ensure_studio_metadata(task)
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
    project_name = (args.project_name or args.title or '').strip().lower()
    goal = (args.goal or '').strip().lower()
    if any(key in project_name for key in ['planning', 'project', '项目']) or any(key in goal for key in ['持续推进', '项目底座', 'project base', '长期跟踪']):
        return 'project_base'
    return 'execution_run'


def main():
    parser = argparse.ArgumentParser(description='create a studio task and ensure persistent runner service')
    parser.add_argument('--task-id')
    parser.add_argument('title')
    parser.add_argument('type', choices=['doc', 'code', 'engineering', 'general'])
    parser.add_argument('goal')
    parser.add_argument('--project-name')
    parser.add_argument('--task-scope', choices=['execution_run', 'project_base'])
    parser.add_argument('--artifact', action='append')
    parser.add_argument('--doc-path')
    parser.add_argument('--workdir')
    parser.add_argument('--watch-file', action='append')
    parser.add_argument('--watch-process-log', action='append')
    parser.add_argument('--notify-target')
    parser.add_argument('--notify-channel', default='telegram')
    parser.add_argument('--notify-policy', default='milestones')
    parser.add_argument('--background', dest='background', action='store_true', default=True)
    parser.add_argument('--foreground', dest='background', action='store_false')
    args = parser.parse_args()

    resumed = False
    task_id = resume_task_if_exists(args)
    if task_id:
        resumed = True
        call(TASK_PY, 'log', task_id, 'studio_start: resumed existing task record', check=False)
    else:
        inferred_scope = infer_task_scope(args)
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
        if args.project_name:
            cmd.extend(['--project-name', args.project_name])
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

    for script in (ROLES_PY, ACTIVE_ROLES_PY, NEXT_ACTIONS_PY, DISPATCH_PLAN_PY):
        subprocess.run([sys.executable, script, task_id], check=True)

    append_kickoff_event(task_id, resumed=resumed)
    call(NOTIFY_PY, '--task-id', task_id, check=False)
    ensure_project_traces(task_id, force_notion=True)

    if args.background:
        subprocess.run([sys.executable, SERVICE_PY, 'ensure', '--interval', '30'], check=True)
    else:
        subprocess.run([sys.executable, RUNNER_PY, 'tick', '--verbose'], check=True)

    print(f'TASK_ID={task_id}')


if __name__ == '__main__':
    main()
