#!/usr/bin/env python3
import argparse
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, "state", "tasks.json")


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {"tasks": []}
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_task(data, task_id):
    for t in data.get("tasks", []):
        if t.get("id") == task_id:
            return t
    return None


def dispatch_required(item):
    if "required" in item and item.get("required") is not None:
        return bool(item.get("required"))
    return (item.get("role") or "") != "second-opinion"


def dispatch_matches(item, *, phase=None, kinds=None, roles=None, agents=None):
    if phase is not None and item.get("phase") != phase:
        return False
    if kinds and item.get("kind") not in kinds:
        return False
    if roles and item.get("role") not in roles:
        return False
    if agents and item.get("agent") not in agents:
        return False
    return True


def required_dispatch_done(dispatch, kinds, phase=None):
    items = [
        item for item in dispatch
        if dispatch_matches(item, phase=phase, kinds=kinds) and dispatch_required(item)
    ]
    if not items:
        return False
    return all(item.get("status") == "done" for item in items)


def any_dispatch_done(dispatch, *, phase=None, kinds=None, roles=None, agents=None):
    return any(
        item.get("status") == "done"
        for item in dispatch
        if dispatch_matches(item, phase=phase, kinds=kinds, roles=roles, agents=agents)
    )


def phase_summary_text(completion, phase, *, legacy_keys=()):
    phase_summaries = completion.get("phase_summaries") or {}
    text = (phase_summaries.get(phase) or "").strip()
    if text:
        return text
    for key in legacy_keys:
        text = (completion.get(key) or "").strip()
        if text:
            return text
    if phase == "final_summary" and completion.get("summary_phase") == "final_summary":
        text = (completion.get("summary") or "").strip()
        if text:
            return text
    return ""


def gate(task):
    task_type = task.get("type")
    phase = task.get("phase")
    task_scope = task.get('task_scope') or 'execution_run'
    artifacts = task.get("artifacts") or []
    logs = "\n".join(x.get("message", "") for x in task.get("logs", []))
    dispatch = task.get("dispatch_history") or task.get("dispatch_plan") or []
    completion = task.get("completion_evidence") or {}
    agent_plan = task.get("agent_plan") or []
    internal_report_text = phase_summary_text(completion, "report", legacy_keys=("internal_report",))
    final_summary_text = phase_summary_text(completion, "final_summary", legacy_keys=("final_summary",))
    pm_wrapup_text = phase_summary_text(completion, "pm_wrapup", legacy_keys=("pm_wrapup_note",))

    has_expression_role = any(item.get("agent") == "gemini" for item in agent_plan)

    # Internal report requires report summary evidence
    internal_report_ready = bool(completion.get("internal_report_ready")) and (
        bool(internal_report_text)
    )
    if not internal_report_ready:
        internal_report_ready = any_dispatch_done(dispatch, phase="report", kinds={"orchestration"})

    # Final summary ready check
    final_summary_ready = bool(completion.get("final_summary_ready")) and bool(final_summary_text)
    if has_expression_role:
        # If expression role exists, it must have finished a final_summary dispatch
        gemini_done = any_dispatch_done(dispatch, phase="final_summary", agents={"gemini"}, kinds={"expression"})
        if not gemini_done:
            final_summary_ready = False
    
    if not final_summary_ready:
        final_summary_ready = any_dispatch_done(dispatch, phase="final_summary", kinds={"orchestration", "expression"}) and bool(final_summary_text)

    # PM wrapup requires pm_wrapup_note
    pm_wrapup_ready = bool(completion.get("pm_wrapup_ready")) and bool(pm_wrapup_text)
    if not pm_wrapup_ready:
        pm_wrapup_ready = any_dispatch_done(dispatch, phase="pm_wrapup", kinds={"orchestration"}) and bool(pm_wrapup_text)

    main_acceptance = bool(completion.get("main_acceptance")) and bool(pm_wrapup_text)

    checks = []
    checks.append({"name": "task_scope_not_project_base", "ok": task_scope != 'project_base', "reason": "project_base tasks must not auto-complete" if task_scope == 'project_base' else ""})
    checks.append({"name": "phase_is_pm_wrapup_or_done", "ok": phase in {"pm_wrapup", "done"}, "reason": f"current phase is {phase}, need pm_wrapup or done"})
    checks.append({"name": "completion_evidence_present", "ok": bool(completion), "reason": "missing substantive completion evidence"})
    checks.append({"name": "artifact_validated", "ok": bool(completion.get('artifact_validated')) or task_type == 'general', "reason": "artifact not explicitly validated"})
    checks.append({"name": "internal_report_ready", "ok": internal_report_ready, "reason": "internal report not completed or missing report text"})
    checks.append({"name": "internal_report_present", "ok": bool(internal_report_text), "reason": "missing internal report text"})
    checks.append({"name": "final_summary_ready", "ok": final_summary_ready, "reason": "final summary not completed (Gemini output required if assigned)"})
    checks.append({"name": "final_summary_present", "ok": bool(final_summary_text), "reason": "missing final summary text"})
    checks.append({"name": "pm_wrapup_ready", "ok": pm_wrapup_ready, "reason": "pm wrapup not completed or missing pm_wrapup_note"})
    checks.append({"name": "pm_wrapup_present", "ok": bool(pm_wrapup_text), "reason": "missing pm wrapup note"})
    checks.append({"name": "main_acceptance", "ok": main_acceptance, "reason": "main acceptance not marked or missing wrapup note"})

    if task_type == "doc":
        has_artifact = any(str(x).endswith(".md") for x in artifacts)
        checks.append({"name": "has_md_artifact", "ok": has_artifact, "reason": "missing markdown artifact" if not has_artifact else ""})
        has_final_check = ("final_check" in logs) or ("最终检查" in logs) or any_dispatch_done(
            dispatch, phase="final_check", kinds={"review", "second-opinion", "orchestration"}
        )
        checks.append({"name": "final_check_seen", "ok": has_final_check, "reason": "no final_check evidence in logs or dispatch history" if not has_final_check else ""})
        review_done = required_dispatch_done(dispatch, {"review", "second-opinion", "cn-review"})
        checks.append({"name": "review_done", "ok": review_done, "reason": "required review dispatch not fully done" if not review_done else ""})
        checks.append({"name": "review_merged", "ok": bool(completion.get('review_merged')), "reason": "review merge not explicitly marked" if not completion.get('review_merged') else ""})
    elif task_type == "code":
        checks.append({"name": "artifact_present", "ok": bool(artifacts), "reason": "no code artifact recorded" if not artifacts else ""})
        review_done = required_dispatch_done(dispatch, {"review", "cn-review", "second-opinion"})
        checks.append({"name": "review_done", "ok": review_done, "reason": "required review dispatch not fully done" if not review_done else ""})
    elif task_type == "engineering":
        checks.append({"name": "artifact_present", "ok": bool(artifacts), "reason": "no engineering artifact recorded" if not artifacts else ""})
    else:
        checks.append({"name": "artifact_or_summary_present", "ok": bool(artifacts) or bool(completion), "reason": "no artifact or completion summary recorded" if not (artifacts or completion) else ""})

    ok = all(item["ok"] for item in checks)
    return {"ok": ok, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description="check whether task can enter done state")
    parser.add_argument("task_id")
    args = parser.parse_args()

    data = load_tasks()
    task = find_task(data, args.task_id)
    if not task:
        raise SystemExit(f"task not found: {args.task_id}")
    print(json.dumps(gate(task), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
