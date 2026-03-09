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


def gate(task):
    task_type = task.get("type")
    phase = task.get("phase")
    artifacts = task.get("artifacts") or []
    logs = "\n".join(x.get("message", "") for x in task.get("logs", []))
    dispatch = task.get("dispatch_history") or task.get("dispatch_plan") or []
    completion = task.get("completion_evidence") or {}

    checks = []
    checks.append({"name": "phase_is_report", "ok": phase == "report", "reason": "current phase is not report" if phase != "report" else ""})
    checks.append({"name": "completion_evidence_present", "ok": bool(completion), "reason": "missing substantive completion evidence" if not completion else ""})
    checks.append({"name": "artifact_validated", "ok": bool(completion.get('artifact_validated')), "reason": "artifact not explicitly validated" if not completion.get('artifact_validated') else ""})
    checks.append({"name": "main_acceptance", "ok": bool(completion.get('main_acceptance')), "reason": "main acceptance not marked" if not completion.get('main_acceptance') else ""})

    if task_type == "doc":
        has_artifact = any(str(x).endswith(".md") for x in artifacts)
        checks.append({"name": "has_md_artifact", "ok": has_artifact, "reason": "missing markdown artifact" if not has_artifact else ""})
        has_final_check = "final_check" in logs or "最终检查" in logs
        checks.append({"name": "final_check_seen", "ok": has_final_check, "reason": "no final_check evidence in logs" if not has_final_check else ""})
        review_done = any(item.get("status") == "done" for item in dispatch if item.get("kind") in {"review", "second-opinion", "cn-review"})
        checks.append({"name": "review_done", "ok": review_done, "reason": "no review-like dispatch done" if not review_done else ""})
        checks.append({"name": "review_merged", "ok": bool(completion.get('review_merged')), "reason": "review merge not explicitly marked" if not completion.get('review_merged') else ""})
        orchestration_done = any(item.get("status") == "done" for item in dispatch if item.get("kind") == "orchestration")
        checks.append({"name": "orchestration_done", "ok": orchestration_done, "reason": "main-agent orchestration not done" if not orchestration_done else ""})
        final_report_evidence = ("最终汇报" in logs) or ("final report" in logs.lower()) or ("输出变更摘要" in logs)
        checks.append({"name": "final_report_evidence", "ok": final_report_evidence, "reason": "no final report evidence in logs" if not final_report_evidence else ""})
    elif task_type == "code":
        checks.append({"name": "artifact_present", "ok": bool(artifacts), "reason": "no code artifact recorded" if not artifacts else ""})
        review_done = any(item.get("status") == "done" for item in dispatch if item.get("kind") in {"review", "orchestration"})
        checks.append({"name": "review_or_orchestration_done", "ok": review_done, "reason": "no review/orchestration dispatch done" if not review_done else ""})
    elif task_type == "engineering":
        checks.append({"name": "artifact_present", "ok": bool(artifacts), "reason": "no engineering artifact recorded" if not artifacts else ""})
        orchestration_done = any(item.get("status") == "done" for item in dispatch if item.get("kind") == "orchestration")
        checks.append({"name": "orchestration_done", "ok": orchestration_done, "reason": "no orchestration dispatch done" if not orchestration_done else ""})
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
