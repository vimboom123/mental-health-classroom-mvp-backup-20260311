#!/usr/bin/env python3
import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

from studio_common import (
    RUNNER_STATE_FILE,
    add_event,
    ensure_notify,
    ensure_notify_state,
    ensure_studio_metadata,
    file_sha256,
    find_task,
    load_json,
    load_tasks,
    mark_events_sent,
    now_iso,
    normalize_path,
    pending_events,
    primary_doc_artifact,
    save_json,
    save_tasks,
    seed_artifact_state,
    sync_execution_artifacts,
    task_state_lock,
    task_artifacts,
    task_workdir,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, 'state')
LOCK_FILE = os.path.join(STATE_DIR, 'runner.lock')
WATCH_PY = os.path.join(BASE_DIR, 'scripts', 'studio_watch.py')
PROCESS_WATCH_PY = os.path.join(BASE_DIR, 'scripts', 'studio_process_watch.py')
SCHEDULER_PY = os.path.join(BASE_DIR, 'scripts', 'studio_scheduler.py')
NOTIFY_PY = os.path.join(BASE_DIR, 'scripts', 'studio_notify.py')
ACTIVE_ROLES_PY = os.path.join(BASE_DIR, 'scripts', 'studio_active_roles.py')
ROLES_PY = os.path.join(BASE_DIR, 'scripts', 'studio_roles.py')
NEXT_ACTIONS_PY = os.path.join(BASE_DIR, 'scripts', 'studio_next_actions.py')
DISPATCH_PLAN_PY = os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_plan.py')
DISPATCH_QUEUE_PY = os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_queue.py')
DISPATCH_LAUNCH_PY = os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_launch.py')
NOTION_SYNC_PY = os.path.join(BASE_DIR, 'scripts', 'studio_notion_project.py')
STATUS_TRACE_PY = os.path.join(BASE_DIR, 'scripts', 'studio_status_trace.py')
DISPATCH_POLL_PY = os.path.join(BASE_DIR, 'scripts', 'studio_dispatch_poll.py')
COMPLETION_GATE_PY = os.path.join(BASE_DIR, 'scripts', 'studio_completion_gate.py')
COMPLETION_SUGGEST_PY = os.path.join(BASE_DIR, 'scripts', 'studio_completion_suggest.py')
TASK_PY = os.path.join(BASE_DIR, 'scripts', 'studio_task.py')
SYNC_TASK_PY = os.path.join(BASE_DIR, 'scripts', 'studio_sync_task_state.py')
STALL_CHECK_PY = os.path.join(BASE_DIR, 'scripts', 'studio_stall_check.py')

TERMINAL_STATUSES = {'done', 'cancelled', 'waiting_user', 'blocked', 'failed'}
ACTIVE_STATUSES = {'queued', 'in_progress', 'waiting_reviewer'}
TERMINAL_DISPATCH = {'done', 'failed'}
PROGRESS_ORDERS = {
    'doc': ['intake', 'review_collect', 'review_merge', 'revise', 'polish', 'final_check', 'report', 'done'],
    'doc_review_only': ['intake', 'review_collect', 'review_merge', 'report', 'done'],
    'code': ['intake', 'plan', 'implement', 'review', 'test', 'fixup', 'report', 'done'],
    'engineering': ['intake', 'investigate', 'execute', 'verify', 'iterate', 'report', 'done'],
    'general': ['intake', 'execute', 'verify', 'report', 'done'],
}
RECOMMENDATIONS = {
    'doc': {
        'intake': ('review_collect', 'waiting_reviewer', '等待 reviewer / 子代理结果回流', 'runner: doc intake -> review_collect'),
        'review_collect': ('review_merge', 'in_progress', '并单 reviewer 意见，生成修改清单', 'runner: doc review_collect -> review_merge'),
        'review_merge': ('revise', 'in_progress', '根据修改清单持续改正文', 'runner: doc review_merge -> revise'),
        'revise': ('polish', 'in_progress', '收尾润色并统一口径', 'runner: doc revise -> polish'),
        'polish': ('final_check', 'in_progress', '做最终检查并准备汇报', 'runner: doc polish -> final_check'),
        'final_check': ('report', 'in_progress', '输出变更摘要与当前结论', 'runner: doc final_check -> report'),
        'report': ('done', 'done', '文档任务完成', 'runner: doc report -> done'),
    },
    'doc_review_only': {
        'intake': ('review_collect', 'waiting_reviewer', '等待 reviewer / 子代理结果回流', 'runner: doc(review_only) intake -> review_collect'),
        'review_collect': ('review_merge', 'in_progress', '并单 reviewer 意见，生成审稿结论', 'runner: doc(review_only) review_collect -> review_merge'),
        'review_merge': ('report', 'in_progress', '输出审稿结论与修改建议，不自动进入改稿', 'runner: doc(review_only) review_merge -> report'),
        'report': ('done', 'done', '审稿任务完成', 'runner: doc(review_only) report -> done'),
    },
    'code': {
        'intake': ('plan', 'in_progress', '拆解实现路径与子任务', 'runner: code intake -> plan'),
        'plan': ('implement', 'in_progress', '进入实现并联动子代理', 'runner: code plan -> implement'),
        'implement': ('review', 'waiting_reviewer', '等待 reviewer / 审阅结果返回', 'runner: code implement -> review'),
        'review': ('test', 'in_progress', '根据 reviewer 结果进入测试', 'runner: code review -> test'),
        'test': ('fixup', 'in_progress', '处理测试问题并收尾', 'runner: code test -> fixup'),
        'fixup': ('report', 'in_progress', '整理结果、风险与后续项', 'runner: code fixup -> report'),
        'report': ('done', 'done', '代码任务完成', 'runner: code report -> done'),
    },
    'engineering': {
        'intake': ('investigate', 'in_progress', '先调查现状、约束与可行路径', 'runner: engineering intake -> investigate'),
        'investigate': ('execute', 'in_progress', '执行当前最优路径', 'runner: engineering investigate -> execute'),
        'execute': ('verify', 'in_progress', '验证结果并判断是否继续迭代', 'runner: engineering execute -> verify'),
        'verify': ('iterate', 'in_progress', '若未完成则继续下一轮推进', 'runner: engineering verify -> iterate'),
        'iterate': ('report', 'in_progress', '整理阶段性产出与阻塞点', 'runner: engineering iterate -> report'),
        'report': ('done', 'done', '工程任务完成', 'runner: engineering report -> done'),
    },
    'general': {
        'intake': ('execute', 'in_progress', '进入执行阶段', 'runner: general intake -> execute'),
        'execute': ('verify', 'in_progress', '验证当前结果', 'runner: general execute -> verify'),
        'verify': ('report', 'in_progress', '整理汇报', 'runner: general verify -> report'),
        'report': ('done', 'done', '任务完成', 'runner: general report -> done'),
    },
}


def call_py(script, *args, check=True):
    return subprocess.run([sys.executable, script, *args], check=check, capture_output=True, text=True)


def acquire_lock(blocking=False):
    os.makedirs(STATE_DIR, exist_ok=True)
    fd = open(LOCK_FILE, 'w')
    flags = fcntl.LOCK_EX
    if not blocking:
        flags |= fcntl.LOCK_NB
    try:
        fcntl.flock(fd.fileno(), flags)
    except BlockingIOError:
        fd.close()
        return None
    fd.seek(0)
    fd.truncate()
    fd.write(str(os.getpid()))
    fd.flush()
    return fd


def refresh_runner_state(mode, **extra):
    state = load_json(RUNNER_STATE_FILE, {'last_tick': None, 'ticks': 0})
    state.update({'mode': mode, 'pid': os.getpid(), 'lease_at': now_iso()})
    state.update(extra)
    save_json(RUNNER_STATE_FILE, state)
    return state


def infer_progress(task_type, phase):
    order = PROGRESS_ORDERS.get(task_type, PROGRESS_ORDERS['general'])
    try:
        idx = order.index(phase)
    except ValueError:
        idx = 0
    current = idx + 1
    total = len(order)
    percent = int((current / total) * 100)
    return {
        'percent': percent,
        'current': current,
        'total': total,
        'status_text': f'当前阶段：{phase}',
    }


def scheduled_ids(max_active=3):
    res = call_py(SCHEDULER_PY, '--max-active', str(max_active), check=False)
    if res.returncode != 0:
        return None, {'code': res.returncode, 'stdout': res.stdout.strip(), 'stderr': res.stderr.strip()}
    payload = json.loads(res.stdout or '{}')
    return {item['id'] for item in payload.get('selected', [])}, payload


def refresh_supporting_state(task_id):
    call_py(ROLES_PY, task_id, check=False)
    call_py(ACTIVE_ROLES_PY, task_id, check=False)
    call_py(NEXT_ACTIONS_PY, task_id, check=False)
    call_py(DISPATCH_PLAN_PY, task_id, check=False)


def load_task(task_id):
    data = load_tasks()
    return data, find_task(data, task_id)


def update_task(task_id, *args):
    return call_py(TASK_PY, 'update', task_id, *args, check=False)


def ensure_task_defaults(task):
    before = json.dumps({
        'notify': task.get('notify'),
        'notify_state': task.get('notify_state'),
        'execution': task.get('execution'),
        'artifacts': task.get('artifacts'),
        'project': task.get('project'),
        'notion': task.get('notion'),
        'status_trace': task.get('status_trace'),
        'reporting': task.get('reporting'),
    }, sort_keys=True, ensure_ascii=False)
    ensure_studio_metadata(task)
    ensure_notify(task)
    ensure_notify_state(task)
    sync_execution_artifacts(task)
    seed_artifact_state(task)
    after = json.dumps({
        'notify': task.get('notify'),
        'notify_state': task.get('notify_state'),
        'execution': task.get('execution'),
        'artifacts': task.get('artifacts'),
        'project': task.get('project'),
        'notion': task.get('notion'),
        'status_trace': task.get('status_trace'),
        'reporting': task.get('reporting'),
    }, sort_keys=True, ensure_ascii=False)
    return before != after


def persist_task_defaults(task_id):
    with task_state_lock():
        data = load_tasks()
        task = find_task(data, task_id)
        if not task:
            return False
        changed = ensure_task_defaults(task)
        if changed:
            save_tasks(data)
        return changed


def missing_binding_reason(task):
    if task.get('type') == 'doc' and not primary_doc_artifact(task):
        return 'doc task missing bound artifact/doc-path'
    if task.get('type') == 'code' and not task_workdir(task):
        return 'code task missing workdir'
    return None


def ingest_watched_files(task):
    results = []
    for path in task.get('watched_files') or []:
        path = normalize_path(path)
        if not path or not os.path.exists(path):
            continue
        res = call_py(WATCH_PY, 'ingest', task['id'], path, '--on-done-phase', infer_done_phase(task), '--on-done-next', infer_done_next(task), check=False)
        results.append({'path': path, 'code': res.returncode, 'stdout': res.stdout.strip(), 'stderr': res.stderr.strip()})
    return results


def ingest_watched_process_logs(task):
    results = []
    for path in task.get('watched_process_logs') or []:
        path = normalize_path(path)
        if not path or not os.path.exists(path):
            continue
        source_key = os.path.basename(path)
        res = call_py(PROCESS_WATCH_PY, task['id'], '--log-file', path, '--source-key', source_key, '--on-done-phase', infer_done_phase(task), '--on-done-next', infer_done_next(task), check=False)
        results.append({'path': path, 'source_key': source_key, 'code': res.returncode, 'stdout': res.stdout.strip(), 'stderr': res.stderr.strip()})
    return results


def infer_done_phase(task):
    task_type = task.get('type')
    phase = task.get('phase')
    if task_type == 'doc' and phase == 'review_collect':
        return 'review_merge'
    if task_type == 'code' and phase in {'implement', 'review'}:
        return 'test'
    if task_type == 'engineering' and phase in {'investigate', 'execute'}:
        return 'verify'
    return phase or 'execute'


def infer_done_next(task):
    task_type = task.get('type')
    if task_type == 'doc':
        return '开始并单 reviewer 意见'
    if task_type == 'code':
        return '开始测试和回归修正'
    if task_type == 'engineering':
        return '开始验证执行结果'
    return '根据新结果继续推进'


def dispatch_items(task):
    return task.get('dispatch_plan') or []


def dispatch_required(item):
    if 'required' in item and item.get('required') is not None:
        return bool(item.get('required'))
    return (item.get('role') or '') != 'second-opinion'


def required_items(task):
    items = dispatch_items(task)
    return [item for item in items if dispatch_required(item)]


def unique_runtime_items(task, *, statuses=None):
    statuses = set(statuses or [])
    seen = set()
    out = []
    for coll in ('dispatch_plan', 'dispatch_history'):
        for item in task.get(coll) or []:
            item_id = item.get('id')
            if not item_id or item_id in seen:
                continue
            if statuses and item.get('status') not in statuses:
                continue
            seen.add(item_id)
            out.append(item)
    return out


def load_runtime_meta(item):
    meta_path = item.get('runtime_meta')
    if not meta_path or not os.path.exists(meta_path):
        return {}
    try:
        return json.loads(open(meta_path, 'r', encoding='utf-8').read())
    except Exception:
        return {}


def soft_role_ready(item):
    status = item.get('status') or 'planned'
    if status in TERMINAL_DISPATCH:
        return True
    meta = load_runtime_meta(item)
    soft_wait = int(meta.get('soft_wait_sec') or 0)
    launched_at = meta.get('launched_at')
    if soft_wait <= 0 or not launched_at:
        return False
    try:
        launched_ts = datetime.fromisoformat(launched_at).timestamp()
    except Exception:
        return False
    return (datetime.now(timezone.utc).timestamp() - launched_ts) >= soft_wait


def phase_ready(task):
    items = dispatch_items(task)
    if not items:
        return True
    required = required_items(task)
    if required:
        if any((item.get('status') or 'planned') in {'planned', 'queued', 'running'} for item in required):
            return False
        if not all(item.get('status') == 'done' for item in required):
            return False
    for item in items:
        if dispatch_required(item):
            if (item.get('status') or 'planned') not in TERMINAL_DISPATCH:
                return False
            continue
        if not soft_role_ready(item):
            return False
    return True


def maybe_queue_phase(task_id):
    data, task = load_task(task_id)
    if not task:
        return None
    items = dispatch_items(task)
    if not any(item.get('status') == 'planned' for item in items):
        return None
    return call_py(DISPATCH_QUEUE_PY, 'queue-next', task_id, check=False)


def maybe_launch_queued(task_id):
    data, task = load_task(task_id)
    if not task:
        return []
    outputs = []
    for item in dispatch_items(task):
        if item.get('status') == 'queued':
            outputs.append(call_py(DISPATCH_LAUNCH_PY, task_id, item.get('id'), check=False))
    return outputs


def maybe_poll_running(task_id):
    data, task = load_task(task_id)
    if not task:
        return []
    outputs = []
    for item in unique_runtime_items(task, statuses={'running'}):
        if item.get('runtime_meta'):
            outputs.append(call_py(DISPATCH_POLL_PY, task_id, item.get('id'), check=False))
    return outputs


def maybe_send_notifications(task_id):
    return call_py(NOTIFY_PY, '--task-id', task_id, check=False)


def sync_project_state(task_id, *, force_notion=False):
    notion_pull = call_py(NOTION_SYNC_PY, 'pull', task_id, check=False)
    notion_args = ['sync', task_id]
    if force_notion:
        notion_args.append('--force')
    else:
        notion_args.extend(['--min-interval', '300'])
    notion = call_py(NOTION_SYNC_PY, *notion_args, check=False)
    trace = call_py(STATUS_TRACE_PY, task_id, check=False)
    return {'notion_pull': notion_pull, 'notion': notion, 'status_trace': trace}


def advance_task(task):
    task_type = 'doc_review_only' if task.get('type') == 'doc' and task.get('mode') == 'review_only' else (task.get('type') or 'general')
    phase = task.get('phase') or 'intake'
    flow = RECOMMENDATIONS.get(task_type, RECOMMENDATIONS['general'])
    if phase not in flow:
        return None
    new_phase, new_status, next_step, log_msg = flow[phase]
    progress = infer_progress(task_type, new_phase)
    res = update_task(
        task['id'],
        '--status', new_status,
        '--phase', new_phase,
        '--next', next_step,
        '--progress-percent', str(progress['percent']),
        '--progress-current', str(progress['current']),
        '--progress-total', str(progress['total']),
        '--progress-status', progress['status_text'],
        '--log', log_msg,
    )
    refresh_supporting_state(task['id'])
    return res


def maybe_complete_report(task):
    suggest_res = call_py(COMPLETION_SUGGEST_PY, task['id'], check=False)
    gate_res = call_py(COMPLETION_GATE_PY, task['id'], check=False)
    try:
        gate_payload = json.loads(gate_res.stdout or '{}')
    except Exception:
        gate_payload = {'ok': False, 'checks': []}
    if gate_payload.get('ok'):
        progress_type = 'doc_review_only' if task.get('type') == 'doc' and task.get('mode') == 'review_only' else (task.get('type') or 'general')
        progress = infer_progress(progress_type, 'done')
        update_task(
            task['id'],
            '--status', 'done',
            '--phase', 'done',
            '--next', '任务完成',
            '--progress-percent', str(progress['percent']),
            '--progress-current', str(progress['current']),
            '--progress-total', str(progress['total']),
            '--progress-status', progress['status_text'],
            '--log', 'runner: acceptance gate satisfied -> done',
        )
        refresh_supporting_state(task['id'])
    return {'suggest': suggest_res, 'gate': gate_res}


def maybe_block_missing(task):
    reason = missing_binding_reason(task)
    if not reason:
        return None
    update_task(task['id'], '--status', 'blocked', '--blocker', reason, '--next', '补齐任务绑定后重试', '--log', f'runner blocked task: {reason}')
    return reason


def tick_once(verbose=False, notify_min_interval=300, max_active=3, lock_fd=None):
    temp_lock = None
    if lock_fd is None:
        temp_lock = acquire_lock(blocking=False)
        if temp_lock is None:
            payload = {'skipped': True, 'reason': 'runner lock busy'}
            print(json.dumps(payload, ensure_ascii=False, indent=2) if verbose else json.dumps(payload, ensure_ascii=False))
            return
    changed = []
    side_effects = []
    notify_task_ids = set()
    now = now_iso()

    ids, sched_payload = scheduled_ids(max_active=max_active)
    side_effects.append({'scheduler': sched_payload})

    data = load_tasks()
    for task in data.get('tasks', []):
        task_id = task.get('id')
        if ensure_task_defaults(task):
            persist_task_defaults(task_id)
            data, task = load_task(task_id)
            if not task:
                continue
        if task.get('agent_plan') is None:
            refresh_supporting_state(task_id)
            data, task = load_task(task_id)
            if not task:
                continue
        if task.get('status') in TERMINAL_STATUSES:
            sync_res = sync_project_state(task_id)
            side_effects.append({'task_id': task_id, 'project_state': {
                'notion': sync_res['notion'].stdout.strip(),
                'status_trace': sync_res['status_trace'].stdout.strip(),
            }})
            if pending_events(task):
                notify_task_ids.add(task_id)
            continue
        if ids is not None and task.get('status') in ACTIVE_STATUSES and task_id not in ids:
            side_effects.append({'task_id': task_id, 'skipped_by_scheduler': True})
            sync_res = sync_project_state(task_id)
            side_effects.append({'task_id': task_id, 'project_state': {'notion': sync_res['notion'].stdout.strip(), 'status_trace': sync_res['status_trace'].stdout.strip()}})
            if pending_events(task):
                notify_task_ids.add(task_id)
            continue
        if maybe_block_missing(task):
            sync_res = sync_project_state(task_id, force_notion=True)
            side_effects.append({'task_id': task_id, 'project_state': {'notion': sync_res['notion'].stdout.strip(), 'status_trace': sync_res['status_trace'].stdout.strip()}})
            notify_task_ids.add(task_id)
            continue

        watch_res = ingest_watched_files(task)
        if watch_res:
            side_effects.append({'task_id': task_id, 'watch': watch_res})
        process_res = ingest_watched_process_logs(task)
        if process_res:
            side_effects.append({'task_id': task_id, 'process_watch': process_res})
        call_py(SYNC_TASK_PY, task_id, check=False)
        refresh_supporting_state(task_id)
        data, task = load_task(task_id)
        if not task:
            continue

        if task.get('phase') == 'report' and phase_ready(task):
            completion_res = maybe_complete_report(task)
            side_effects.append({'task_id': task_id, 'completion': {'suggest': completion_res['suggest'].stdout.strip(), 'gate': completion_res['gate'].stdout.strip()}})
            sync_res = sync_project_state(task_id, force_notion=True)
            side_effects.append({'task_id': task_id, 'project_state': {'notion': sync_res['notion'].stdout.strip(), 'status_trace': sync_res['status_trace'].stdout.strip()}})
            notify_task_ids.add(task_id)
            continue
        if phase_ready(task):
            res = advance_task(task)
            if res is not None:
                changed.append({'task_id': task_id, 'advanced_from': task.get('phase')})
                side_effects.append({'task_id': task_id, 'advance': {'code': res.returncode, 'stdout': res.stdout.strip(), 'stderr': res.stderr.strip()}})
            sync_res = sync_project_state(task_id, force_notion=True)
            side_effects.append({'task_id': task_id, 'project_state': {'notion': sync_res['notion'].stdout.strip(), 'status_trace': sync_res['status_trace'].stdout.strip()}})
            notify_task_ids.add(task_id)
            continue

        queue_res = maybe_queue_phase(task_id)
        if queue_res:
            side_effects.append({'task_id': task_id, 'dispatch_queue': {'code': queue_res.returncode, 'stdout': queue_res.stdout.strip(), 'stderr': queue_res.stderr.strip()}})
        launch_res_list = maybe_launch_queued(task_id)
        for res in launch_res_list:
            side_effects.append({'task_id': task_id, 'dispatch_launch': {'code': res.returncode, 'stdout': res.stdout.strip(), 'stderr': res.stderr.strip()}})
        poll_res_list = maybe_poll_running(task_id)
        for res in poll_res_list:
            side_effects.append({'task_id': task_id, 'dispatch_poll': {'code': res.returncode, 'stdout': res.stdout.strip(), 'stderr': res.stderr.strip()}})

        data, task = load_task(task_id)
        if not task:
            continue
        stall_res = call_py(STALL_CHECK_PY, task_id, '--stall-seconds', '180', check=False)
        if stall_res.returncode == 0:
            try:
                stall_payload = json.loads(stall_res.stdout or '{}')
            except Exception:
                stall_payload = {}
            if stall_payload.get('stalled'):
                side_effects.append({'task_id': task_id, 'stalled': stall_payload})

        if task.get('phase') == 'report' and phase_ready(task):
            completion_res = maybe_complete_report(task)
            side_effects.append({'task_id': task_id, 'completion': {'suggest': completion_res['suggest'].stdout.strip(), 'gate': completion_res['gate'].stdout.strip()}})
            data, task = load_task(task_id)
            if not task:
                continue
            sync_res = sync_project_state(task_id, force_notion=True)
            side_effects.append({'task_id': task_id, 'project_state': {'notion': sync_res['notion'].stdout.strip(), 'status_trace': sync_res['status_trace'].stdout.strip()}})
            notify_task_ids.add(task_id)
        elif phase_ready(task):
            res = advance_task(task)
            if res is not None:
                changed.append({'task_id': task_id, 'advanced_from': task.get('phase')})
                side_effects.append({'task_id': task_id, 'advance': {'code': res.returncode, 'stdout': res.stdout.strip(), 'stderr': res.stderr.strip()}})
            sync_res = sync_project_state(task_id, force_notion=True)
            side_effects.append({'task_id': task_id, 'project_state': {'notion': sync_res['notion'].stdout.strip(), 'status_trace': sync_res['status_trace'].stdout.strip()}})
            notify_task_ids.add(task_id)
        elif pending_events(task):
            sync_res = sync_project_state(task_id)
            side_effects.append({'task_id': task_id, 'project_state': {'notion': sync_res['notion'].stdout.strip(), 'status_trace': sync_res['status_trace'].stdout.strip()}})
            notify_task_ids.add(task_id)

    if notify_task_ids:
        latest = load_tasks()
        for task in latest.get('tasks', []):
            if task.get('id') in notify_task_ids or pending_events(task):
                if pending_events(task):
                    res = maybe_send_notifications(task.get('id'))
                    side_effects.append({
                        'task_id': task.get('id'),
                        'notify': {
                            'code': res.returncode,
                            'stdout': res.stdout.strip(),
                            'stderr': res.stderr.strip(),
                        },
                    })
    else:
        latest = load_tasks()
        retried = False
        for task in latest.get('tasks', []):
            if pending_events(task):
                retried = True
                res = maybe_send_notifications(task.get('id'))
                side_effects.append({
                    'task_id': task.get('id'),
                    'notify_retry': {
                        'code': res.returncode,
                        'stdout': res.stdout.strip(),
                        'stderr': res.stderr.strip(),
                    },
                })
        if retried:
            changed.append({'notify_retry': True})
    state = load_json(RUNNER_STATE_FILE, {'last_tick': None, 'ticks': 0})
    state['last_tick'] = now
    state['ticks'] = int(state.get('ticks', 0)) + 1
    state['pid'] = os.getpid()
    state['lease_at'] = now
    save_json(RUNNER_STATE_FILE, state)
    payload = {'time': now, 'changed': changed, 'side_effects': side_effects, 'ticks': state['ticks']}
    print(json.dumps(payload, ensure_ascii=False, indent=2) if verbose else json.dumps(changed, ensure_ascii=False))
    if temp_lock is not None:
        temp_lock.close()


def daemon_loop(interval, max_ticks, verbose=False, notify_min_interval=300, max_active=3):
    lock_fd = acquire_lock(blocking=False)
    if lock_fd is None:
        raise SystemExit('studio runner already active')
    refresh_runner_state('daemon', started_at=now_iso(), interval=interval)
    ticks = 0
    while True:
        tick_once(verbose=verbose, notify_min_interval=notify_min_interval, max_active=max_active, lock_fd=lock_fd)
        ticks += 1
        refresh_runner_state('daemon', started_at=load_json(RUNNER_STATE_FILE, {}).get('started_at') or now_iso(), interval=interval)
        if max_ticks and ticks >= max_ticks:
            break
        time.sleep(interval)
    lock_fd.close()


def main():
    parser = argparse.ArgumentParser(description='studio orchestrator runner')
    sub = parser.add_subparsers(dest='command', required=True)
    tick = sub.add_parser('tick')
    tick.add_argument('--verbose', action='store_true')
    tick.add_argument('--notify-min-interval', type=int, default=300)
    tick.add_argument('--max-active', type=int, default=3)
    daemon = sub.add_parser('daemon')
    daemon.add_argument('--interval', type=int, default=30)
    daemon.add_argument('--max-ticks', type=int, default=0)
    daemon.add_argument('--verbose', action='store_true')
    daemon.add_argument('--notify-min-interval', type=int, default=300)
    daemon.add_argument('--max-active', type=int, default=3)
    args = parser.parse_args()
    if args.command == 'tick':
        refresh_runner_state('tick')
        tick_once(verbose=args.verbose, notify_min_interval=args.notify_min_interval, max_active=args.max_active)
    else:
        daemon_loop(args.interval, args.max_ticks, verbose=args.verbose, notify_min_interval=args.notify_min_interval, max_active=args.max_active)


if __name__ == '__main__':
    main()
