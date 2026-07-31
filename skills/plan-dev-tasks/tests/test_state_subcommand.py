from pathlib import Path
import json
import subprocess
import tempfile
from typing import Optional
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "git-workflow.sh"

SHA = "a" * 40


class StateSubcommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp = Path(self.temp_dir.name)
        # Deliberately NOT a Git repository: state recording must work on
        # non-Git workspaces.
        self.project = self.temp / "project"
        self.project.mkdir()

    def run_script(
        self, *args: str, cwd: Optional[Path] = None
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args],
            cwd=cwd or self.project,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_success(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def make_owner(self, task_id: str = "task-one") -> Path:
        task_dir = self.project / ".tmp" / task_id
        task_dir.mkdir(parents=True)
        marker = {
            "task_id": task_id,
            "project_root": str(self.project.resolve()),
            "task_directory": str(task_dir.resolve()),
            "created_by": "plan-dev-tasks",
        }
        (task_dir / "task-owner.json").write_text(
            json.dumps(marker), encoding="utf-8"
        )
        return task_dir

    def state_file(self, task_id: str = "task-one") -> Path:
        return self.project / ".tmp" / task_id / "state.json"

    def load_state(self, task_id: str = "task-one") -> dict:
        return json.loads(self.state_file(task_id).read_text(encoding="utf-8"))

    def init(
        self,
        task_id: str = "task-one",
        versions: str = "plan=v1,context=v1,task=v1",
    ) -> subprocess.CompletedProcess:
        return self.run_script(
            "state", "--init", "--project-root", str(self.project),
            "--task-id", task_id, "--versions", versions,
        )

    def fast_forward(self, task_id: str = "task-one") -> None:
        """Walk the legal lifecycle chain up to `reviewing`."""
        self.assert_success(self.init(task_id))
        self.assert_success(self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", task_id,
            "--gate", self.gate_args(),
        ))
        self.assert_success(self.run_script(
            "state", "--to", "dispatched", "--project-root",
            str(self.project), "--task-id", task_id,
            "--worker", "handle=w1,transport=Agent(dev-with-tdd)",
        ))
        for lifecycle in ("authorized", "running", "handoff-received",
                          "reviewing"):
            self.assert_success(self.run_script(
                "state", "--to", lifecycle, "--project-root",
                str(self.project), "--task-id", task_id,
            ))

    def gate_args(self, **overrides: str) -> str:
        base = {
            "status": "passed",
            "approval_event": "ExitPlanMode approved",
            "plan_version": "v1",
            "context_version": "v1",
            "task_version": "v1",
            "dispatch_mode": "foreground",
            "worker_transport": "Agent(dev-with-tdd)",
            "verify_result": "passed",
            "head": SHA,
        }
        base.update(overrides)
        return ",".join(f"{k}={v}" for k, v in base.items())

    def test_init_creates_valid_state_file_on_non_git_project(self) -> None:
        self.make_owner()

        result = self.init()

        self.assert_success(result)
        data = self.load_state()
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["task_id"], "task-one")
        self.assertEqual(data["lifecycle"], "approved")
        self.assertEqual(data["gate"]["status"], "pending")
        self.assertEqual(data["gate"]["blocked_reason"], "none")
        self.assertEqual(data["versions"], {"plan": "v1", "context": "v1", "task": "v1"})
        self.assertEqual(data["packets"], [])
        self.assertEqual(len(data["transitions"]), 1)
        self.assertIn("task_id\ttask-one", result.stdout)
        self.assertIn("lifecycle\tapproved", result.stdout)

    def test_init_rejects_existing_file(self) -> None:
        self.make_owner()
        self.assert_success(self.init())

        result = self.init()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("state.json already exists", result.stderr)

    def test_init_requires_versions(self) -> None:
        self.make_owner()

        result = self.run_script(
            "state", "--init", "--project-root", str(self.project),
            "--task-id", "task-one",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires --versions", result.stderr)

    def test_init_rejects_incomplete_versions(self) -> None:
        self.make_owner()

        result = self.init(versions="plan=v1,task=v1")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing version: context", result.stderr)
        self.assertFalse(self.state_file().exists())

    def test_missing_owner_rejected(self) -> None:
        # Task directory exists but carries no task-owner.json marker.
        (self.project / ".tmp" / "task-one").mkdir(parents=True)

        result = self.init()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing task-owner.json", result.stderr)

    def test_illegal_transition_rejected(self) -> None:
        self.make_owner()
        self.assert_success(self.init())

        result = self.run_script(
            "state", "--to", "dispatched", "--project-root",
            str(self.project), "--task-id", "task-one",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("illegal state transition: approved -> dispatched", result.stderr)
        self.assertEqual(self.load_state()["lifecycle"], "approved")

    def test_to_prepared_requires_gate_passed(self) -> None:
        self.make_owner()
        self.assert_success(self.init())

        result = self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", "task-one",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires gate passed", result.stderr)

    def test_gate_version_mismatch_rejected(self) -> None:
        self.make_owner()
        self.assert_success(self.init())

        result = self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--gate", self.gate_args(plan_version="v2"),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match versions", result.stderr)

    def test_invalid_gate_enum_rejected(self) -> None:
        self.make_owner()
        self.assert_success(self.init())

        result = self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--gate", self.gate_args(status="bogus"),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid gate status", result.stderr)

    def test_unknown_gate_field_rejected(self) -> None:
        self.make_owner()
        self.assert_success(self.init())

        result = self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--gate", "status=passed,evil=yes",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown gate field: evil", result.stderr)

    def test_to_dispatched_requires_worker_transport(self) -> None:
        self.make_owner()
        self.assert_success(self.init())
        self.assert_success(self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--gate", self.gate_args(),
        ))

        result = self.run_script(
            "state", "--to", "dispatched", "--project-root",
            str(self.project), "--task-id", "task-one",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires worker transport", result.stderr)

    def test_to_blocked_requires_blocked_reason(self) -> None:
        self.make_owner()
        self.fast_forward()

        result = self.run_script(
            "state", "--to", "blocked", "--project-root",
            str(self.project), "--task-id", "task-one",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires a blocked reason", result.stderr)

    def test_blocked_marks_gate_blocked_reason(self) -> None:
        self.make_owner()
        self.fast_forward()

        result = self.run_script(
            "state", "--to", "blocked", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--gate", "blocked_reason=coordinator_direct_write",
            "--evidence", "approval now invalid",
        )

        self.assert_success(result)
        data = self.load_state()
        self.assertEqual(data["lifecycle"], "blocked")
        self.assertEqual(data["gate"]["blocked_reason"], "coordinator_direct_write")
        self.assertEqual(data["transitions"][-1]["evidence"], "approval now invalid")

    def test_packet_registration_and_merge(self) -> None:
        self.make_owner()
        self.assert_success(self.init())
        self.assert_success(self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--gate", self.gate_args(),
            "--packet",
            f"id=P1,worktree={self.project},allowed_write_paths=src/foo,tests/bar",
        ))

        data = self.load_state()
        self.assertEqual(len(data["packets"]), 1)
        packet = data["packets"][0]
        self.assertEqual(packet["packet_id"], "P1")
        self.assertEqual(packet["allowed_write_paths"], ["src/foo", "tests/bar"])
        self.assertEqual(packet["lifecycle"], "approved")

        # Same id merges; a new id appends.
        self.assert_success(self.run_script(
            "state", "--to", "dispatched", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--worker", "handle=w1,transport=Agent(dev-with-tdd)",
            "--packet", f"id=P1,lifecycle=running,expected_head={SHA}",
        ))
        data = self.load_state()
        self.assertEqual(len(data["packets"]), 1)
        self.assertEqual(data["packets"][0]["lifecycle"], "running")
        self.assertEqual(data["packets"][0]["expected_head"], SHA)
        self.assertEqual(data["packets"][0]["allowed_write_paths"], ["src/foo", "tests/bar"])

    def test_packet_requires_id(self) -> None:
        self.make_owner()
        self.assert_success(self.init())

        result = self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--gate", self.gate_args(),
            "--packet", "worktree=x",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("packet requires id", result.stderr)

    def test_unsafe_write_path_rejected(self) -> None:
        self.make_owner()
        self.assert_success(self.init())

        result = self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--gate", self.gate_args(),
            "--packet", "id=P1,allowed_write_paths=../evil",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe write path", result.stderr)

    def test_corrupt_state_file_fails_closed(self) -> None:
        self.make_owner()
        self.assert_success(self.init())
        self.state_file().write_text("{not json", encoding="utf-8")

        result = self.run_script(
            "state", "--show", "--project-root",
            str(self.project), "--task-id", "task-one",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid state.json", result.stderr)

    def test_full_lifecycle_and_show(self) -> None:
        self.make_owner()
        self.assert_success(self.init())
        self.assert_success(self.run_script(
            "state", "--to", "prepared", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--gate", self.gate_args(),
        ))
        self.assert_success(self.run_script(
            "state", "--to", "dispatched", "--project-root",
            str(self.project), "--task-id", "task-one",
            "--worker", "handle=w1,transport=Agent(dev-with-tdd)",
        ))
        for lifecycle in ("authorized", "running", "handoff-received",
                          "reviewing", "accepted", "committed", "finalized"):
            self.assert_success(self.run_script(
                "state", "--to", lifecycle, "--project-root",
                str(self.project), "--task-id", "task-one",
            ))

        show = self.run_script(
            "state", "--show", "--project-root",
            str(self.project), "--task-id", "task-one",
        )
        self.assert_success(show)
        self.assertIn("lifecycle\tfinalized", show.stdout)
        self.assertIn("gate_status\tpassed", show.stdout)
        self.assertEqual(self.load_state()["lifecycle"], "finalized")

        # Terminal state: no further transitions.
        result = self.run_script(
            "state", "--to", "approved", "--project-root",
            str(self.project), "--task-id", "task-one",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("illegal state transition", result.stderr)

    def test_failed_transition_leaves_no_partial_file(self) -> None:
        self.make_owner()
        self.assert_success(self.init())
        before = self.state_file().read_text(encoding="utf-8")

        result = self.run_script(
            "state", "--to", "dispatched", "--project-root",
            str(self.project), "--task-id", "task-one",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state_file().read_text(encoding="utf-8"), before)
        self.assertFalse(self.state_file().with_suffix(".json.tmp").exists())

    def test_task_id_path_traversal_rejected(self) -> None:
        self.make_owner()

        result = self.run_script(
            "state", "--init", "--project-root", str(self.project),
            "--task-id", "../evil", "--versions", "plan=v1,context=v1,task=v1",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe task ID", result.stderr)


if __name__ == "__main__":
    unittest.main()
