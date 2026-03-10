#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from studio_common import (
    ensure_project,
    ensure_reporting,
    ensure_studio_metadata,
    find_task,
    load_json,
    load_tasks,
    now_iso,
    save_json,
    save_tasks,
    task_state_lock,
)

API_BASE = 'https://api.notion.com/v1'
NOTION_VERSION = '2025-09-03'
DATA_SOURCE_ID = '478ee9d7-d1db-4dc7-85d8-7663db95d6ca'
API_KEY_FILE = os.path.expanduser('~/.config/notion/api_key')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_SOURCE_CACHE_FILE = os.path.join(BASE_DIR, 'state', 'notion_data_source_cache.json')
DATA_SOURCE_CACHE_TTL_SEC = 600
MANAGED_SOURCE = 'studio-orchestrator'
AGENT_LABELS = {
    'main': 'Main',
    'codex': 'Codex',
    'gemini': 'Gemini',
    'claude-code': 'Claude Code',
    'oracle': 'Oracle',
    'qwen': 'Qwen',
}
EXTRA_PROPERTIES = {
    '任务ID': {'rich_text': {}},
    '阶段细节': {'rich_text': {}},
    '当前负责人': {'rich_text': {}},
    '等待对象': {'rich_text': {}},
    '完成证据': {'rich_text': {}},
    '替代关系': {'rich_text': {}},
    '系统来源': {'rich_text': {}},
    '同步诊断': {'rich_text': {}},
}


def read_api_key() -> str:
    if not os.path.exists(API_KEY_FILE):
        raise SystemExit('NOTION_API_KEY_MISSING')
    return open(API_KEY_FILE, 'r', encoding='utf-8').read().strip()


def notion_request(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        API_BASE + path,
        data=body,
        method=method,
        headers={
            'Authorization': f'Bearer {read_api_key()}',
            'Notion-Version': NOTION_VERSION,
            'Content-Type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        text = exc.read().decode('utf-8', errors='ignore')
        raise SystemExit(f'NOTION_HTTP_{exc.code}: {text}')


def parse_ts(value: Optional[str]) -> float:
    if not value:
        return 0.0
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def short_text(value: Optional[str], limit: int = 1900) -> str:
    text = (value or '').strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + '…'


def cached_data_source_info(*, max_age_sec: int = DATA_SOURCE_CACHE_TTL_SEC) -> Dict[str, Any]:
    cache = load_json(DATA_SOURCE_CACHE_FILE, {})
    checked_at = parse_ts(cache.get('checked_at'))
    if checked_at and cache.get('info'):
        age = datetime.now(timezone.utc).timestamp() - checked_at
        if age < max_age_sec:
            return cache['info']
    info = notion_request('GET', f'/data_sources/{DATA_SOURCE_ID}')
    save_json(DATA_SOURCE_CACHE_FILE, {'checked_at': now_iso(), 'info': info})
    return info


def ensure_data_source_schema() -> Dict[str, Any]:
    info = cached_data_source_info()
    props = info.get('properties') or {}
    missing = {name: spec for name, spec in EXTRA_PROPERTIES.items() if name not in props}
    if not missing:
        return info
    updated = notion_request('PATCH', f'/data_sources/{DATA_SOURCE_ID}', {'properties': missing})
    save_json(DATA_SOURCE_CACHE_FILE, {'checked_at': now_iso(), 'info': updated})
    return updated


def data_source_has_property(name: str) -> bool:
    info = cached_data_source_info()
    return name in (info.get('properties') or {})


def title_prop(text: str) -> Dict[str, Any]:
    return {'title': [{'text': {'content': text[:2000]}}]}


def rich_text_prop(text: str) -> Dict[str, Any]:
    return {'rich_text': [{'text': {'content': text[:2000]}}]} if text else {'rich_text': []}


def select_prop(name: str) -> Dict[str, Any]:
    return {'select': {'name': name}}


def multi_select_prop(names) -> Dict[str, Any]:
    return {'multi_select': [{'name': name} for name in names if name]}


def date_prop(value: Optional[str]) -> Dict[str, Any]:
    return {'date': {'start': value}} if value else {'date': None}


def priority_name(task: Dict[str, Any]) -> str:
    value = int(task.get('priority') or 50)
    if value <= 10:
        return 'P0'
    if value <= 30:
        return 'P1'
    if value <= 60:
        return 'P2'
    return 'P3'


def status_name(task: Dict[str, Any]) -> str:
    status = task.get('status')
    if status == 'done':
        return '已完成'
    if status == 'waiting_reviewer':
        return '待审核'
    if status == 'waiting_user':
        return '待验收'
    if status in {'blocked', 'failed', 'cancelled'}:
        return '已暂停'
    return '进行中'


def role_names(task: Dict[str, Any]):
    names = ['负责人']
    for item in task.get('agent_plan') or []:
        label = AGENT_LABELS.get(item.get('agent'))
        if item.get('agent') == 'main':
            label = None
        if label and label not in names:
            names.append(label)
    return names


def extract_rich_text(prop: Dict[str, Any]) -> str:
    parts = prop.get('rich_text') or []
    return ''.join(part.get('plain_text', '') for part in parts)


def extract_title(prop: Dict[str, Any]) -> str:
    parts = prop.get('title') or []
    return ''.join(part.get('plain_text', '') for part in parts)


def actor_label(item: Dict[str, Any]) -> str:
    role = item.get('role') or 'role'
    agent = AGENT_LABELS.get(item.get('agent'), item.get('agent') or '?')
    return f'{role}({agent})'


def unique_actor_labels(items: List[Dict[str, Any]], limit: int = 4) -> List[str]:
    labels = []
    seen = set()
    for item in items:
        label = actor_label(item)
        if label in seen:
            continue
        seen.add(label)
        labels.append(label)
        if len(labels) >= limit:
            break
    return labels


def current_phase_dispatches(task: Dict[str, Any], statuses: Optional[set] = None) -> List[Dict[str, Any]]:
    phase = task.get('phase')
    dispatches = task.get('dispatch_history') or task.get('dispatch_plan') or []
    out = []
    for item in dispatches:
        if phase and item.get('phase') != phase:
            continue
        if statuses and item.get('status') not in statuses:
            continue
        out.append(item)
    return out


def current_owner(task: Dict[str, Any]) -> str:
    if task.get('status') in {'done', 'cancelled'}:
        return task.get('owner') or 'main-agent'
    running = current_phase_dispatches(task, {'running'})
    if running:
        return ' | '.join(unique_actor_labels(running))
    queued = current_phase_dispatches(task, {'queued'})
    if queued:
        return ' | '.join(unique_actor_labels(queued))
    active = task.get('active_roles') or []
    if active:
        return ' | '.join(unique_actor_labels(active))
    return task.get('owner') or 'main-agent'


def waiting_on(task: Dict[str, Any]) -> str:
    if task.get('status') == 'waiting_user':
        return 'user-acceptance'
    if task.get('blocker'):
        return short_text(f"blocked: {task.get('blocker')}")
    pending = current_phase_dispatches(task, {'planned', 'queued', 'running'})
    if pending:
        return ' | '.join(unique_actor_labels(pending))
    if task.get('status') == 'waiting_reviewer':
        reviewers = [item for item in (task.get('active_roles') or []) if item.get('role') in {'reviewer', 'second-opinion', 'cn-reviewer'}]
        if reviewers:
            return ' | '.join(unique_actor_labels(reviewers))
    return ''


def completion_summary(task: Dict[str, Any]) -> str:
    completion = task.get('completion_evidence') or {}
    if not completion:
        return ''
    parts = [
        f"review_merged={'yes' if completion.get('review_merged') else 'no'}",
        f"artifact_validated={'yes' if completion.get('artifact_validated') else 'no'}",
        f"main_acceptance={'yes' if completion.get('main_acceptance') else 'no'}",
    ]
    if completion.get('marked_at'):
        parts.append(f"marked_at={completion.get('marked_at')}")
    summary = short_text((completion.get('summary') or '').splitlines()[0], limit=600) if completion.get('summary') else ''
    if summary:
        parts.append(summary)
    return short_text(' | '.join(parts))


def replacement_note(task: Dict[str, Any]) -> str:
    for key in ('superseded_by', 'replacement_task_id', 'replacement_project', 'replaced_by'):
        if task.get(key):
            return short_text(f'{key}={task.get(key)}')
    return ''


def sync_source(task: Dict[str, Any]) -> str:
    return MANAGED_SOURCE


def sync_diagnostic(task: Dict[str, Any]) -> str:
    notion = task.get('notion') or {}
    snapshot = notion.get('last_snapshot') or {}
    notes = []
    if snapshot.get('任务ID') and snapshot.get('任务ID') != task.get('id'):
        notes.append(f"remote_task_id={snapshot.get('任务ID')}")
    if snapshot.get('系统来源') and snapshot.get('系统来源') != MANAGED_SOURCE:
        notes.append(f"remote_source={snapshot.get('系统来源')}")
    if task.get('status') in {'done', 'cancelled'} and (task.get('reporting') or {}).get('next_report_at'):
        notes.append('terminal_task_has_next_report')
    return short_text(' | '.join(notes))


def snapshot_from_page(page: Dict[str, Any]) -> Dict[str, Any]:
    props = page.get('properties') or {}
    return {
        'found': True,
        'id': page.get('id'),
        'url': page.get('url'),
        'last_edited_time': page.get('last_edited_time'),
        '项目': extract_title(props.get('项目') or {}),
        '任务ID': extract_rich_text(props.get('任务ID') or {}),
        '状态': ((props.get('状态') or {}).get('select') or {}).get('name'),
        '优先级': ((props.get('优先级') or {}).get('select') or {}).get('name'),
        '负责人': extract_rich_text(props.get('负责人') or {}),
        '当前负责人': extract_rich_text(props.get('当前负责人') or {}),
        '等待对象': extract_rich_text(props.get('等待对象') or {}),
        '参与角色': [item.get('name') for item in ((props.get('参与角色') or {}).get('multi_select') or [])],
        '阶段细节': extract_rich_text(props.get('阶段细节') or {}),
        '交付物': extract_rich_text(props.get('交付物') or {}),
        '风险': extract_rich_text(props.get('风险') or {}),
        '备注': extract_rich_text(props.get('备注') or {}),
        '完成证据': extract_rich_text(props.get('完成证据') or {}),
        '替代关系': extract_rich_text(props.get('替代关系') or {}),
        '系统来源': extract_rich_text(props.get('系统来源') or {}),
        '同步诊断': extract_rich_text(props.get('同步诊断') or {}),
        '下一次汇报': ((props.get('下一次汇报') or {}).get('date') or {}).get('start'),
    }


def project_delivery(task: Dict[str, Any]) -> str:
    artifacts = task.get('artifacts') or []
    if artifacts:
        names = [os.path.basename(path) for path in artifacts[:12]]
        text = ' | '.join(names)
        return short_text(text, limit=1800)
    return (task.get('goal') or '')[:180]


def project_note(task: Dict[str, Any]) -> str:
    parts = [
        f"目标: {task.get('goal') or '-'}",
        f"阶段: {task.get('phase') or '-'} / {task.get('status') or '-'}",
        f"当前负责人: {current_owner(task) or '-'}",
        f"等待对象: {waiting_on(task) or '-'}",
        f"下一步: {task.get('next') or '-'}",
    ]
    return ' | '.join(parts)[:1900]


def current_risk(task: Dict[str, Any]) -> str:
    risks = []
    if task.get('blocker'):
        risks.append(str(task['blocker']))
    for item in reversed(task.get('dispatch_history') or []):
        if item.get('status') == 'failed':
            note = item.get('note') or f"{item.get('role')} failed"
            risks.append(str(note))
            break
    diag = sync_diagnostic(task)
    if diag:
        risks.append(f'diag={diag}')
    return short_text(' | '.join(risks))


def desired_properties(task: Dict[str, Any]) -> Dict[str, Any]:
    ensure_studio_metadata(task)
    project = ensure_project(task)
    reporting = ensure_reporting(task)
    return {
        '项目': title_prop(project['name']),
        '任务ID': rich_text_prop(task.get('id') or ''),
        '状态': select_prop(status_name(task)),
        '优先级': select_prop(priority_name(task)),
        '负责人': rich_text_prop(task.get('owner') or 'main-agent'),
        '当前负责人': rich_text_prop(current_owner(task)),
        '等待对象': rich_text_prop(waiting_on(task)),
        '参与角色': multi_select_prop(role_names(task)),
        '阶段细节': rich_text_prop(f"{task.get('phase') or '-'} / {task.get('status') or '-'}"),
        '交付物': rich_text_prop(project_delivery(task)),
        '风险': rich_text_prop(current_risk(task)),
        '备注': rich_text_prop(project_note(task)),
        '完成证据': rich_text_prop(completion_summary(task)),
        '替代关系': rich_text_prop(replacement_note(task)),
        '系统来源': rich_text_prop(sync_source(task)),
        '同步诊断': rich_text_prop(sync_diagnostic(task)),
        '下一次汇报': date_prop(reporting.get('next_report_at')),
    }


def desired_hash(task: Dict[str, Any]) -> str:
    payload = desired_properties(task)
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


def fetch_database_id(task: Dict[str, Any]) -> str:
    notion = task.setdefault('notion', {})
    if notion.get('database_id'):
        return notion['database_id']
    info = cached_data_source_info(max_age_sec=0)
    database_id = info.get('parent', {}).get('database_id') or info.get('database_id')
    if not database_id:
        raise SystemExit('NOTION_DATABASE_ID_MISSING')
    notion['database_id'] = database_id
    notion['data_source_id'] = DATA_SOURCE_ID
    return database_id


def query_pages(filter_payload: Optional[Dict[str, Any]] = None, *, page_size: int = 100) -> List[Dict[str, Any]]:
    results = []
    cursor = None
    while True:
        payload: Dict[str, Any] = {'page_size': min(page_size, 100)}
        if filter_payload:
            payload['filter'] = filter_payload
        if cursor:
            payload['start_cursor'] = cursor
        resp = notion_request('POST', f'/data_sources/{DATA_SOURCE_ID}/query', payload)
        results.extend(resp.get('results') or [])
        if not resp.get('has_more'):
            return results
        cursor = resp.get('next_cursor')
        if not cursor:
            return results


def query_first(filter_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    results = query_pages(filter_payload, page_size=20)
    return results[0] if results else None


def query_by_title(project_name: str) -> Optional[Dict[str, Any]]:
    if not project_name:
        return None
    return query_first({
        'property': '项目',
        'title': {'equals': project_name},
    })


def query_by_task_id(task_id: str) -> Optional[Dict[str, Any]]:
    if not task_id or not data_source_has_property('任务ID'):
        return None
    payload = {
        'property': '任务ID',
        'rich_text': {'equals': task_id},
    }
    return query_first(payload)


def get_page(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    notion = task.setdefault('notion', {})
    if notion.get('page_id'):
        try:
            return notion_request('GET', f"/pages/{notion['page_id']}")
        except SystemExit:
            pass
    page = query_by_task_id(task.get('id') or '')
    if page:
        return page
    project = ensure_project(task)
    return query_by_title(project['name'])


def update_task_notion(task: Dict[str, Any], page: Dict[str, Any], sync_hash: Optional[str], *, pulled: bool = False) -> Dict[str, Any]:
    snapshot = snapshot_from_page(page)
    project = ensure_project(task)
    reporting = ensure_reporting(task)
    notion = task.setdefault('notion', {})
    notion['page_id'] = snapshot['id']
    notion['url'] = snapshot['url']
    notion['last_snapshot'] = snapshot
    notion['data_source_id'] = DATA_SOURCE_ID
    notion['last_pull_at' if pulled else 'last_sync_at'] = now_iso()
    if sync_hash:
        notion['last_sync_hash'] = sync_hash
    if snapshot.get('项目'):
        project['name'] = snapshot['项目']
    reporting['next_report_at'] = snapshot.get('下一次汇报') or None
    return snapshot


def sync_task(task: Dict[str, Any], *, force: bool = False, min_interval: int = 300) -> Dict[str, Any]:
    ensure_studio_metadata(task)
    ensure_data_source_schema()
    notion = task.setdefault('notion', {})
    sync_hash = desired_hash(task)
    if not force and notion.get('page_id') and notion.get('last_sync_hash') == sync_hash and notion.get('last_sync_at'):
        try:
            last = datetime.fromisoformat(notion['last_sync_at']).timestamp()
            if (datetime.now(timezone.utc).timestamp() - last) < min_interval:
                snapshot = notion.get('last_snapshot') or {'found': False}
                return {'action': 'skipped', 'snapshot': snapshot}
        except Exception:
            pass
    page = get_page(task)
    props = desired_properties(task)
    if page:
        result = notion_request('PATCH', f"/pages/{page['id']}", {'properties': props})
        action = 'updated'
    else:
        result = notion_request('POST', '/pages', {
            'parent': {'database_id': fetch_database_id(task)},
            'properties': props,
        })
        action = 'created'
    snapshot = update_task_notion(task, result, sync_hash)
    return {'action': action, 'snapshot': snapshot}


def pull_task(task: Dict[str, Any]) -> Dict[str, Any]:
    ensure_studio_metadata(task)
    page = get_page(task)
    if not page:
        task.setdefault('notion', {})['last_snapshot'] = {'found': False}
        task['notion']['last_pull_at'] = now_iso()
        return {'action': 'missing', 'snapshot': {'found': False}}
    snapshot = update_task_notion(task, page, None, pulled=True)
    return {'action': 'pulled', 'snapshot': snapshot}


def audit_payload() -> Dict[str, Any]:
    data = load_tasks()
    tasks = data.get('tasks', [])
    pages = query_pages(page_size=100)

    local_by_id = {task.get('id'): task for task in tasks if task.get('id')}
    local_by_title = {}
    for task in tasks:
        project = ensure_project(task)
        local_by_title[project.get('name')] = task

    remote_by_page_id = {}
    remote_by_task_id = {}
    remote_by_title = {}
    remote_orphans = []
    remote_untracked_open = []
    remote_managed_missing_task_id = []
    drift = []
    local_missing_remote = []

    for page in pages:
        snapshot = snapshot_from_page(page)
        remote_by_page_id[snapshot.get('id')] = snapshot
        if snapshot.get('任务ID'):
            remote_by_task_id[snapshot.get('任务ID')] = snapshot
        if snapshot.get('项目'):
            remote_by_title[snapshot.get('项目')] = snapshot

        status = snapshot.get('状态')
        title = snapshot.get('项目')
        task_id = snapshot.get('任务ID')
        source = snapshot.get('系统来源')
        if task_id and task_id not in local_by_id:
            remote_orphans.append({
                'task_id': task_id,
                'project': title,
                'status': status,
                'url': snapshot.get('url'),
            })
        elif not task_id and source == MANAGED_SOURCE:
            remote_managed_missing_task_id.append({
                'project': title,
                'status': status,
                'url': snapshot.get('url'),
            })
        elif not task_id and status != '已完成' and title not in local_by_title:
            remote_untracked_open.append({
                'project': title,
                'status': status,
                'current_owner': snapshot.get('当前负责人') or snapshot.get('负责人'),
                'url': snapshot.get('url'),
            })

    for task in tasks:
        project = ensure_project(task)
        notion = task.get('notion') or {}
        snapshot = (
            remote_by_page_id.get(notion.get('page_id'))
            or remote_by_task_id.get(task.get('id'))
            or remote_by_title.get(project.get('name'))
        )
        if not snapshot:
            local_missing_remote.append({
                'task_id': task.get('id'),
                'project': project.get('name'),
                'status': task.get('status'),
            })
            continue

        checks = {}
        local_status = status_name(task)
        local_owner = current_owner(task)
        local_waiting = waiting_on(task)
        local_next_report = (task.get('reporting') or {}).get('next_report_at') or None
        if snapshot.get('状态') != local_status:
            checks['状态'] = {'local': local_status, 'remote': snapshot.get('状态')}
        if (snapshot.get('当前负责人') or '') != local_owner:
            checks['当前负责人'] = {'local': local_owner, 'remote': snapshot.get('当前负责人') or ''}
        if (snapshot.get('等待对象') or '') != local_waiting:
            checks['等待对象'] = {'local': local_waiting, 'remote': snapshot.get('等待对象') or ''}
        if (snapshot.get('下一次汇报') or None) != local_next_report:
            checks['下一次汇报'] = {'local': local_next_report, 'remote': snapshot.get('下一次汇报') or None}
        if checks:
            drift.append({
                'task_id': task.get('id'),
                'project': project.get('name'),
                'url': snapshot.get('url'),
                'checks': checks,
            })

    return {
        'counts': {
            'local_tasks': len(tasks),
            'remote_pages': len(pages),
            'remote_orphans': len(remote_orphans),
            'remote_untracked_open': len(remote_untracked_open),
            'remote_managed_missing_task_id': len(remote_managed_missing_task_id),
            'local_missing_remote': len(local_missing_remote),
            'drift': len(drift),
        },
        'remote_orphans': remote_orphans,
        'remote_untracked_open': remote_untracked_open,
        'remote_managed_missing_task_id': remote_managed_missing_task_id,
        'local_missing_remote': local_missing_remote,
        'drift': drift,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='sync studio task with Notion project base')
    sub = parser.add_subparsers(dest='command', required=True)

    sync = sub.add_parser('sync')
    sync.add_argument('task_id')
    sync.add_argument('--force', action='store_true')
    sync.add_argument('--min-interval', type=int, default=300)

    pull = sub.add_parser('pull')
    pull.add_argument('task_id')

    sub.add_parser('audit')

    args = parser.parse_args()
    if args.command == 'audit':
        print(json.dumps(audit_payload(), ensure_ascii=False, indent=2))
        return

    with task_state_lock():
        data = load_tasks()
        task = find_task(data, args.task_id)
        if not task:
            raise SystemExit(f'task not found: {args.task_id}')

        if args.command == 'sync':
            payload = sync_task(task, force=args.force, min_interval=args.min_interval)
        else:
            payload = pull_task(task)

        task['updated_at'] = now_iso()
        save_tasks(data)
    out = {
        'task_id': task.get('id'),
        'project': (task.get('project') or {}).get('name'),
        'action': payload['action'],
        'notion': task.get('notion'),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
