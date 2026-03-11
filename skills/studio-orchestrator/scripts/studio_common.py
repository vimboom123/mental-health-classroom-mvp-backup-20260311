#!/usr/bin/env python3
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import fcntl

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
STATE_DIR = os.path.join(BASE_DIR, "state")
TASKS_FILE = os.path.join(STATE_DIR, "tasks.json")
TASKS_LAST_GOOD_FILE = os.path.join(STATE_DIR, "tasks.last-good.json")
TASKS_LOCK_FILE = os.path.join(STATE_DIR, "tasks.json.lock")
RUNNER_STATE_FILE = os.path.join(STATE_DIR, "runner_state.json")
SESSIONS_FILE = os.path.expanduser("~/.openclaw/agents/main/sessions/sessions.json")
STUDIO_SERVICE_LABEL = "ai.openclaw.studio-runner"
DEFAULT_NOTIFY_POLICY = "milestones"
STUDIO_STATUS_DIR = os.path.join(WORKSPACE, "studio", "status")
REPORT_HOURS = (8, 12, 20)
LOCAL_TZ = timezone(timedelta(hours=8))
NON_RESUMABLE_STATUSES = {"done", "cancelled"}
TERMINAL_REPORT_STATUSES = {"done", "cancelled"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def next_report_iso(now: Optional[datetime] = None) -> str:
    current = now or datetime.now(timezone.utc).astimezone(LOCAL_TZ)
    for hour in REPORT_HOURS:
        candidate = current.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > current:
            return candidate.isoformat(timespec="seconds")
    candidate = (current + timedelta(days=1)).replace(hour=REPORT_HOURS[0], minute=0, second=0, microsecond=0)
    return candidate.isoformat(timespec="seconds")


def sync_reporting_state(
    task: Dict[str, Any],
    reporting: Optional[Dict[str, Any]] = None,
    *,
    sent_report_at: Optional[str] = None,
) -> Dict[str, Any]:
    reporting = reporting or task.setdefault("reporting", {})
    status = task.get("status")
    if sent_report_at:
        reporting["last_report_at"] = sent_report_at
    if status in TERMINAL_REPORT_STATUSES:
        reporting["next_report_at"] = None
        return reporting
    if sent_report_at or not reporting.get("next_report_at"):
        reporting["next_report_at"] = next_report_iso()
    return reporting


def slugify(text: Optional[str], fallback: str = "studio-task") -> str:
    raw = (text or "").strip().lower()
    norm = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    if norm:
        return norm[:64]
    seed = (text or fallback).encode("utf-8", errors="ignore")
    return f"{fallback}-{hashlib.sha1(seed).hexdigest()[:10]}"


def ensure_state_dir() -> None:
    os.makedirs(STATE_DIR, exist_ok=True)


def _is_task_container(data: Any) -> bool:
    return isinstance(data, dict) and isinstance(data.get("tasks"), list)


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return default
    if not text.strip():
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        try:
            data, end = decoder.raw_decode(text)
        except json.JSONDecodeError:
            return default
        tail = text[end:].strip()
        if tail:
            save_json(path + ".recovered-tail.json", {"tail": tail})
        save_json(path, data)
        return data


def save_json(path: str, data: Any) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp.", dir=parent or ".")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def load_tasks() -> Dict[str, Any]:
    ensure_state_dir()
    data = load_json(TASKS_FILE, None)
    if _is_task_container(data):
        try:
            save_json(TASKS_LAST_GOOD_FILE, data)
        except Exception:
            pass
        return data

    last_good = load_json(TASKS_LAST_GOOD_FILE, None)
    if _is_task_container(last_good):
        try:
            save_json(TASKS_FILE, last_good)
        except Exception:
            pass
        return last_good
    return {"tasks": []}


def save_tasks(data: Dict[str, Any]) -> None:
    payload = data if _is_task_container(data) else {"tasks": []}
    save_json(TASKS_FILE, payload)
    try:
        save_json(TASKS_LAST_GOOD_FILE, payload)
    except Exception:
        pass


@contextmanager
def task_state_lock():
    ensure_state_dir()
    with open(TASKS_LOCK_FILE, "w", encoding="utf-8") as lockf:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def find_task(data: Dict[str, Any], task_id: str) -> Optional[Dict[str, Any]]:
    for task in data.get("tasks", []):
        if task.get("id") == task_id:
            return task
    return None


def task_brief(task: Optional[Dict[str, Any]]) -> str:
    if not task:
        return '-'
    task_id = task.get('id') or '-'
    title = (task.get('title') or '').strip()
    project = ((task.get('project') or {}).get('name') or '').strip()
    label = title or project or 'untitled'
    return f"{task_id} · {label}"


def linked_task_brief(data: Dict[str, Any], task_id: Optional[str]) -> str:
    if not task_id:
        return '-'
    task = find_task(data, task_id)
    if not task:
        return str(task_id)
    return task_brief(task)


def linked_task_briefs(data: Dict[str, Any], task_ids: Optional[List[str]]) -> List[str]:
    items = []
    for task_id in task_ids or []:
        items.append(linked_task_brief(data, task_id))
    return items


def parse_iso_ts(value: Optional[str]) -> float:
    if not value:
        return 0.0
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def child_tasks(data: Dict[str, Any], task: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = []
    for task_id in task.get('child_task_ids') or []:
        child = find_task(data, task_id)
        if child:
            items.append(child)
    items.sort(key=lambda item: parse_iso_ts(item.get('updated_at')), reverse=True)
    return items


def _first_meaningful_line(text: Optional[str]) -> str:
    for raw in (text or '').splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(('任务 ', 'phase=', 'instruction=', 'done_dispatch=', 'artifacts:')):
            continue
        if line.startswith('- /'):
            continue
        if line.startswith('结论：'):
            return line.removeprefix('结论：').strip()
        if '=' in line:
            key, value = line.split('=', 1)
            if key in {'goal', 'summary', 'next', 'status'} and value.strip():
                return value.strip()
        return line
    return ''


def _human_child_summary(task: Dict[str, Any]) -> str:
    completion = task.get('completion_evidence') or {}
    summary = _first_meaningful_line(completion.get('summary') or '')
    if summary:
        return summary
    goal = (task.get('goal') or '').strip()
    phase = task.get('phase') or '-'
    status = task.get('status') or '-'
    if goal:
        if status == 'done':
            return f"已完成：{goal}"
        return f"进行中：{goal}（{phase}）"
    return f"{task_brief(task)}：{phase} / {status}"


def _human_child_next(task: Dict[str, Any]) -> str:
    next_step = (task.get('next') or '').strip()
    if not next_step or next_step == '任务完成':
        if task.get('status') == 'done':
            return '该子任务已完成，准备派生下一轮 execution_run'
        return ''
    return next_step


def project_base_rollup(data: Dict[str, Any], task: Dict[str, Any], limit: int = 3) -> Dict[str, Any]:
    children = child_tasks(data, task)
    recent = children[:limit]
    recent_briefs = [task_brief(item) for item in recent]
    done_count = len([item for item in children if item.get('status') == 'done'])
    active_count = len([item for item in children if item.get('status') not in {'done', 'cancelled'}])
    latest = recent[0] if recent else None
    latest_summary = ''
    latest_next = ''
    latest_risk = ''
    if latest:
        latest_summary = _human_child_summary(latest)
        latest_next = _human_child_next(latest)
        latest_risk = (latest.get('blocker') or '').strip()
    artifact_count = len(task.get('artifacts') or [])
    completion_text = (
        f"project_base_active=yes | artifact_count={artifact_count} | children={len(children)} | done={done_count} | active={active_count} | "
        f"recent_children={'；'.join(recent_briefs) if recent_briefs else '暂无子任务'} | latest={latest_summary or '暂无最近执行摘要'}"
    )
    note_parts = [
        f"任务层级: {task.get('task_scope') or 'project_base'}",
        f"目标: {task.get('goal') or '-'}",
        f"阶段: {task.get('phase') or '-'} / {task.get('status') or '-'}",
        f"当前负责人: {task.get('current_owner') or task.get('owner') or '-'}",
        f"等待对象: {task.get('waiting_on') or '-'}",
        f"下一步: {task.get('next') or '-'}",
    ]
    if recent_briefs:
        note_parts.append('最近子任务: ' + '；'.join(recent_briefs))
    if latest_summary:
        note_parts.append('最近进展: ' + latest_summary)
    if latest_next:
        note_parts.append('子任务下一步: ' + latest_next)
    if latest_risk:
        note_parts.append('子任务风险: ' + latest_risk)
    return {
        'child_count': len(children),
        'done_count': done_count,
        'active_count': active_count,
        'recent_briefs': recent_briefs,
        'latest_task': latest,
        'latest_summary': latest_summary,
        'latest_next': latest_next,
        'latest_risk': latest_risk,
        'completion_text': completion_text,
        'note_text': ' | '.join(note_parts)[:1900],
    }


def same_path(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False
    return normalize_path(a) == normalize_path(b)


def task_identity_keys(task: Dict[str, Any]) -> Dict[str, Any]:
    project = ensure_project(task)
    return {
        "project_name": project.get("name"),
        "project_slug": project.get("slug"),
        "title": task.get("title"),
        "workdir": task_workdir(task),
        "artifacts": set(task_artifacts(task)),
    }


def find_resume_candidate(
    data: Dict[str, Any],
    *,
    task_id: Optional[str] = None,
    title: Optional[str] = None,
    project_name: Optional[str] = None,
    workdir: Optional[str] = None,
    artifacts: Optional[List[str]] = None,
    preferred_scope: Optional[str] = None,
    parent_task_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if task_id:
        return find_task(data, task_id)

    wanted_artifacts = {normalize_path(path) for path in (artifacts or []) if normalize_path(path)}
    wanted_project = (project_name or "").strip()
    wanted_title = (title or "").strip()
    wanted_slug = slugify(wanted_project or wanted_title) if (wanted_project or wanted_title) else None
    workdir_norm = normalize_path(workdir)
    wanted_scope = (preferred_scope or "").strip() or None
    wanted_parent = (parent_task_id or "").strip() or None

    candidates = []
    for task in data.get("tasks", []):
        if task.get("status") in NON_RESUMABLE_STATUSES:
            continue
        task_scope = task.get("task_scope") or "execution_run"
        if wanted_scope and task_scope != wanted_scope:
            continue
        score = 0
        ident = task_identity_keys(task)
        if wanted_parent and task.get("parent_task_id") == wanted_parent:
            score += 110
        if wanted_project and ident["project_name"] == wanted_project:
            score += 100
        if wanted_slug and ident["project_slug"] == wanted_slug:
            score += 90
        if wanted_title and task.get("title") == wanted_title:
            score += 60
        if workdir_norm and same_path(ident["workdir"], workdir_norm):
            score += 80
        if wanted_artifacts:
            overlap = len(ident["artifacts"] & wanted_artifacts)
            score += overlap * 20
        if score > 0:
            candidates.append((score, task.get("updated_at") or "", task))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def strip_channel_target(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if ":" in value:
        prefix, rest = value.split(":", 1)
        if prefix in {"telegram", "whatsapp", "imessage", "discord", "slack"} and rest:
            return rest
    return value


def resolve_default_notify() -> Optional[Dict[str, str]]:
    data = load_json(SESSIONS_FILE, {})
    main = data.get("agent:main:main") or {}
    delivery = main.get("deliveryContext") or {}
    origin = main.get("origin") or {}
    channel = delivery.get("channel") or origin.get("provider")
    if channel != "telegram":
        return None
    target = strip_channel_target(delivery.get("to") or origin.get("from"))
    if not target:
        return None
    return {"channel": "telegram", "target": str(target), "policy": DEFAULT_NOTIFY_POLICY}


def normalize_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return os.path.abspath(os.path.expanduser(path))


def normalize_paths(paths: Optional[List[str]]) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in paths or []:
        path = normalize_path(raw)
        if not path or path in seen:
            continue
        seen.add(path)
        out.append(path)
    return out


def artifact_noise(path: Optional[str]) -> bool:
    if not path:
        return False
    norm = str(path).replace("\\", "/")
    base = os.path.basename(norm)
    parts = [part for part in norm.split("/") if part]
    return (
        base.startswith(".")
        or base in {"__pycache__", ".DS_Store", ".pytest_cache"}
        or norm.endswith((".pyc", ".pyo"))
        or "__pycache__" in parts
        or ".pytest_cache" in parts
    )


def ensure_project(task: Dict[str, Any]) -> Dict[str, Any]:
    project = task.setdefault("project", {})
    name = project.get("name") or task.get("title") or task.get("id") or "studio-task"
    slug = project.get("slug") or slugify(name, fallback=task.get("id") or "studio-task")
    project["name"] = name
    project["slug"] = slug
    return project


def ensure_reporting(task: Dict[str, Any]) -> Dict[str, Any]:
    reporting = task.setdefault("reporting", {})
    reporting.setdefault("last_report_at", None)
    reporting.setdefault("source", "studio")
    return sync_reporting_state(task, reporting)


def ensure_notion(task: Dict[str, Any]) -> Dict[str, Any]:
    notion = task.setdefault("notion", {})
    notion.setdefault("page_id", None)
    notion.setdefault("url", None)
    notion.setdefault("database_id", None)
    notion.setdefault("data_source_id", "478ee9d7-d1db-4dc7-85d8-7663db95d6ca")
    notion.setdefault("last_sync_at", None)
    notion.setdefault("last_pull_at", None)
    notion.setdefault("last_snapshot", None)
    notion.setdefault("last_sync_hash", None)
    return notion


def ensure_status_trace(task: Dict[str, Any]) -> Dict[str, Any]:
    project = ensure_project(task)
    trace = task.setdefault("status_trace", {})
    task_scope = task.get("task_scope") or "execution_run"
    if task_scope == "project_base":
        trace_name = f"{project['slug']}.md"
    else:
        trace_name = f"{project['slug']}--{task.get('id') or 'task'}.md"
    default_path = os.path.join(STUDIO_STATUS_DIR, trace_name)
    current = normalize_path(trace.get("path"))
    # Migrate legacy per-project trace path for execution_run tasks to per-task files.
    legacy_project_path = normalize_path(os.path.join(STUDIO_STATUS_DIR, f"{project['slug']}.md"))
    if not current or (task_scope != "project_base" and current == legacy_project_path):
        current = normalize_path(default_path)
    trace["path"] = current
    trace.setdefault("last_sync_at", None)
    return trace


def normalize_quality_mode(value: Optional[str]) -> str:
    raw = (value or "").strip().lower()
    if raw in {"quality_first", "quality-first", "high", "highest"}:
        return "strict"
    if raw in {"default", "normal"}:
        return "balanced"
    if raw in {"fast", "performance"}:
        return "speed"
    if raw:
        return raw
    return "strict"


def ensure_quality(task: Dict[str, Any]) -> str:
    mode = normalize_quality_mode(task.get("quality_mode") or task.get("quality_priority"))
    task["quality_mode"] = mode
    if not str(task.get("quality_priority") or "").strip():
        task["quality_priority"] = "quality" if mode == "strict" else mode
    return mode


def ensure_studio_metadata(task: Dict[str, Any]) -> None:
    ensure_quality(task)
    ensure_project(task)
    ensure_reporting(task)
    ensure_notion(task)
    ensure_status_trace(task)


def file_sha256(path: str) -> Optional[str]:
    if not os.path.exists(path) or not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_execution(task: Dict[str, Any]) -> Dict[str, Any]:
    ensure_studio_metadata(task)
    execution = task.setdefault("execution", {})
    execution.setdefault("workdir", None)
    execution.setdefault("artifacts", list(task.get("artifacts") or []))
    execution.setdefault("artifact_state", {})
    return execution


def sync_execution_artifacts(task: Dict[str, Any]) -> List[str]:
    execution = ensure_execution(task)
    top_level = normalize_paths(task.get("artifacts") or [])
    exec_level = normalize_paths(execution.get("artifacts") or [])
    merged = normalize_paths(top_level + exec_level)
    if (task.get("type") or "") in {"code", "engineering"}:
        merged = [path for path in merged if not artifact_noise(path)]
    task["artifacts"] = merged
    execution["artifacts"] = merged
    return merged


def seed_artifact_state(task: Dict[str, Any]) -> None:
    execution = ensure_execution(task)
    state = execution.setdefault("artifact_state", {})
    for path in sync_execution_artifacts(task):
        entry = state.setdefault(path, {})
        entry.setdefault("baseline_sha256", file_sha256(path))
        entry.setdefault("last_seen_sha256", file_sha256(path))


def task_workdir(task: Dict[str, Any]) -> Optional[str]:
    execution = ensure_execution(task)
    return normalize_path(execution.get("workdir"))


def task_artifacts(task: Dict[str, Any]) -> List[str]:
    return sync_execution_artifacts(task)


def primary_doc_artifact(task: Dict[str, Any]) -> Optional[str]:
    for path in task_artifacts(task):
        if str(path).lower().endswith(".md"):
            return path
    return None


def ensure_notify(task: Dict[str, Any], default_if_missing: bool = True) -> Optional[Dict[str, Any]]:
    ensure_studio_metadata(task)
    notify = task.get("notify")
    if not notify and default_if_missing:
        notify = resolve_default_notify()
    if not notify:
        task["notify"] = None
        return None
    notify = dict(notify)
    notify["channel"] = notify.get("channel") or "telegram"
    notify["target"] = strip_channel_target(notify.get("target"))
    notify["policy"] = notify.get("policy") or DEFAULT_NOTIFY_POLICY
    task["notify"] = notify
    return notify


def ensure_notify_state(task: Dict[str, Any]) -> Dict[str, Any]:
    ensure_studio_metadata(task)
    state = task.setdefault("notify_state", {})
    state.setdefault("events", [])
    state.setdefault("sent_event_keys", [])
    return state


def render_event_text(task: Dict[str, Any], title: str, detail_lines: List[str]) -> str:
    lines = [f"[{task.get('id')}] {task.get('title')}", title]
    lines.extend([line for line in detail_lines if line])
    return "\n".join(lines)


def add_event(
    task: Dict[str, Any],
    *,
    key: str,
    kind: str,
    title: str,
    detail_lines: List[str],
    phase: Optional[str] = None,
    status: Optional[str] = None,
    next_step: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> bool:
    ensure_notify(task)
    state = ensure_notify_state(task)
    sent_keys = set(state.get("sent_event_keys") or [])
    existing = {event.get("key") for event in state.get("events") or []}
    if key in sent_keys or key in existing:
        return False
    event = {
        "key": key,
        "kind": kind,
        "title": title,
        "text": render_event_text(task, title, detail_lines),
        "phase": phase or task.get("phase"),
        "status": status or task.get("status"),
        "next": next_step or task.get("next"),
        "meta": meta or {},
        "created_at": now_iso(),
        "sent_at": None,
    }
    state.setdefault("events", []).append(event)
    return True


def pending_events(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    state = ensure_notify_state(task)
    return [event for event in (state.get("events") or []) if not event.get("sent_at")]


def mark_events_sent(task: Dict[str, Any], keys: List[str]) -> int:
    keys_set = set(keys)
    if not keys_set:
        return 0
    state = ensure_notify_state(task)
    sent = 0
    sent_at = None
    for event in state.get("events") or []:
        if event.get("key") in keys_set and not event.get("sent_at"):
            if sent_at is None:
                sent_at = now_iso()
            event["sent_at"] = sent_at
            sent += 1
    sent_keys = state.setdefault("sent_event_keys", [])
    for key in keys:
        if key not in sent_keys:
            sent_keys.append(key)
    if sent:
        sync_reporting_state(task, sent_report_at=sent_at)
    return sent
