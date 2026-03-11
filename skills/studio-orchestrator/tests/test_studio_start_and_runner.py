import os
import sys
import tempfile
import threading
import time
import unittest
from argparse import Namespace
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import studio_common
import studio_runner
import studio_start


class StudioStateSandbox:
    def __init__(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.status_dir = self.root / "status"
        self.status_dir.mkdir(parents=True, exist_ok=True)
        self._originals = {}

    def patch(self, module, name, value):
        key = (module, name)
        if key not in self._originals:
            self._originals[key] = getattr(module, name)
        setattr(module, name, value)

    def __enter__(self):
        self.patch(studio_common, "STATE_DIR", str(self.root))
        self.patch(studio_common, "TASKS_FILE", str(self.root / "tasks.json"))
        self.patch(studio_common, "TASKS_LAST_GOOD_FILE", str(self.root / "tasks.last-good.json"))
        self.patch(studio_common, "TASKS_LOCK_FILE", str(self.root / "tasks.json.lock"))
        self.patch(studio_common, "RUNNER_STATE_FILE", str(self.root / "runner_state.json"))
        self.patch(studio_common, "STUDIO_STATUS_DIR", str(self.status_dir))
        self.patch(studio_common, "resolve_default_notify", lambda: None)
        return self

    def __exit__(self, exc_type, exc, tb):
        for (module, name), value in reversed(list(self._originals.items())):
            setattr(module, name, value)
        self._tmpdir.cleanup()


def seed_tasks(payload):
    with studio_common.task_state_lock():
        studio_common.save_tasks(payload)


def load_task(task_id):
    data = studio_common.load_tasks()
    return studio_common.find_task(data, task_id)


class StudioStartScopeTests(unittest.TestCase):
    def make_args(self, workdir, artifact):
        return Namespace(
            task_id=None,
            title="Website MVP execution restart 20260311",
            type="general",
            goal="基于网站项目底座 58398a10 重新拉起一轮 execution run，继续推进大学生心理健康教育网站的实现与前端成品化",
            project_name="Mental health classroom website planning",
            task_scope=None,
            parent_task_id=None,
            artifact=[artifact],
            doc_path=None,
            workdir=workdir,
            watch_file=[],
            watch_process_log=[],
            notify_target=None,
            notify_channel="telegram",
            notify_policy="milestones",
            quality_mode="strict",
            quality_priority="quality",
            execution_mode="serial",
            serial_queue_json=None,
            agent_plan_json=None,
            background=False,
        )

    def test_execution_run_restart_does_not_resume_project_base(self):
        with StudioStateSandbox() as sandbox:
            workdir = str(sandbox.root / "studio-project")
            artifact = str(sandbox.root / "studio-project" / "website-product-plan-v1.md")
            payload = {
                "tasks": [
                    {
                        "id": "58398a10",
                        "title": "Mental health classroom website planning",
                        "type": "general",
                        "task_scope": "project_base",
                        "status": "blocked",
                        "phase": "execute",
                        "goal": "持续推进大学生心理健康教育网站项目",
                        "next": "项目底座保留，等待下一轮 execution_run",
                        "project": {
                            "name": "Mental health classroom website planning",
                            "slug": "mental-health-classroom-website-planning",
                        },
                        "artifacts": [artifact],
                        "execution": {
                            "workdir": workdir,
                            "artifacts": [artifact],
                            "artifact_state": {},
                        },
                        "notify_state": {"events": [], "sent_event_keys": []},
                        "logs": [],
                        "created_at": "2026-03-10T09:00:02+08:00",
                        "updated_at": "2026-03-10T22:02:46+08:00",
                        "child_task_ids": ["c08da1e9"],
                    },
                    {
                        "id": "c08da1e9",
                        "title": "Website MVP execution - page skeleton and API prep",
                        "type": "general",
                        "task_scope": "execution_run",
                        "parent_task_id": "58398a10",
                        "status": "done",
                        "phase": "done",
                        "goal": "按网站 MVP 清单进入真实执行",
                        "next": "任务完成",
                        "project": {
                            "name": "Mental health classroom website planning",
                            "slug": "mental-health-classroom-website-planning",
                        },
                        "artifacts": [artifact],
                        "execution": {
                            "workdir": workdir,
                            "artifacts": [artifact],
                            "artifact_state": {},
                        },
                        "notify_state": {"events": [], "sent_event_keys": []},
                        "logs": [],
                        "created_at": "2026-03-10T10:00:00+08:00",
                        "updated_at": "2026-03-10T11:00:00+08:00",
                    },
                ]
            }
            seed_tasks(payload)
            args = self.make_args(workdir, artifact)

            self.assertEqual(studio_start.infer_task_scope(args), "execution_run")
            resumed_task_id = studio_start.resume_task_if_exists(args, preferred_scope="execution_run")
            self.assertEqual(resumed_task_id, "")
            self.assertEqual(studio_start.infer_parent_task_id(args, task_scope="execution_run"), "58398a10")

            project_base = load_task("58398a10")
            self.assertIsNotNone(project_base)
            self.assertEqual(project_base["title"], "Mental health classroom website planning")
            self.assertEqual(project_base["goal"], "持续推进大学生心理健康教育网站项目")
            self.assertEqual(project_base["status"], "blocked")


class StudioRunnerLockRetryTests(unittest.TestCase):
    def test_acquire_lock_with_retry_waits_and_recovers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_state_dir = studio_runner.STATE_DIR
            original_lock_file = studio_runner.LOCK_FILE
            studio_runner.STATE_DIR = tmpdir
            studio_runner.LOCK_FILE = os.path.join(tmpdir, "runner.lock")
            holder = None
            try:
                holder = studio_runner.acquire_lock(blocking=False)
                self.assertIsNotNone(holder)
                result = {}

                def contender():
                    start = time.monotonic()
                    fd, retries = studio_runner.acquire_lock_with_retry(
                        blocking=False,
                        retries=6,
                        delay_ms=50,
                    )
                    result["elapsed"] = time.monotonic() - start
                    result["fd"] = fd
                    result["retries"] = retries

                thread = threading.Thread(target=contender)
                thread.start()
                time.sleep(0.16)
                holder.close()
                holder = None
                thread.join(timeout=2)

                self.assertIn("fd", result)
                self.assertIsNotNone(result["fd"])
                self.assertGreaterEqual(result["retries"], 2)
                self.assertGreaterEqual(result["elapsed"], 0.10)
                result["fd"].close()
            finally:
                if holder is not None:
                    holder.close()
                studio_runner.STATE_DIR = original_state_dir
                studio_runner.LOCK_FILE = original_lock_file


if __name__ == "__main__":
    unittest.main()
