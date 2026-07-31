from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / "scripts" / "hooks"
PRETOOL = HOOKS_DIR / "pretool_guard.py"
STOP = HOOKS_DIR / "stop_guard.py"
RUNNER = ROOT / "scripts" / "git-workflow.sh"
SHA = "a" * 40


def run_hook(script: Path, event: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
    )


class HookDecisionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()
        self.task_dir = self.root / ".tmp" / "t1"
        self.task_dir.mkdir(parents=True)

    def write_state(self, lifecycle: str = "approved",
                    gate_status: str = "pending", packets=None) -> None:
        gate = {
            "status": gate_status, "blocked_reason": "none",
            "approval_event": "", "plan_version": "v1",
            "context_version": "v1", "task_version": "v1",
            "dispatch_mode": "unknown", "worker_transport": "",
            "verify_result": "not-applicable", "head": "not-applicable",
            "verified_at": None,
        }
        data = {
            "schema_version": 1,
            "task_id": "t1",
            "project_root": str(self.root.resolve()),
            "task_directory": str(self.task_dir.resolve()),
            "created_at": "2026-07-31T00:00:00+00:00",
            "lifecycle": lifecycle,
            "gate": gate,
            "versions": {"plan": "v1", "context": "v1", "task": "v1"},
            "packets": packets or [],
            "worker": {"handle": None, "transport": None},
            "transitions": [{"from": "none", "to": lifecycle,
                             "at": "2026-07-31T00:00:00+00:00",
                             "evidence": "init"}],
        }
        (self.task_dir / "state.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    def active_packets(self, worktree=None, paths=("src/foo",)):
        return [{
            "packet_id": "P1",
            "lifecycle": "running",
            "task_branch": None,
            "worktree": str(worktree or self.root.resolve()),
            "expected_head": SHA,
            "allowed_write_paths": list(paths),
        }]

    def pretool(self, tool_name: str, tool_input: dict,
                agent_type: str = "") -> subprocess.CompletedProcess:
        return run_hook(PRETOOL, {
            "tool_name": tool_name, "cwd": str(self.root),
            "tool_input": tool_input, "agent_type": agent_type,
        })

    def assert_silent(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(result.returncode, 0,
                         msg=f"stderr:\n{result.stderr}")
        self.assertEqual(result.stdout, "",
                         msg=f"unexpected decision:\n{result.stdout}")

    def assert_deny(self, result: subprocess.CompletedProcess,
                    reason: str) -> None:
        self.assertEqual(result.returncode, 0,
                         msg=f"stderr:\n{result.stderr}")
        self.assertIn(reason, result.stdout)

    def test_no_state_file_is_dormant(self) -> None:
        self.assert_silent(self.pretool("Write", {"file_path": "src/x.py"}))

    def test_main_business_write_blocked_while_task_active(self) -> None:
        self.write_state(lifecycle="prepared", gate_status="passed",
                         packets=self.active_packets())
        self.assert_deny(
            self.pretool("Write", {"file_path": "src/foo/main.py"}),
            "coordinator_direct_write",
        )

    def test_main_task_workspace_write_allowed(self) -> None:
        self.write_state(lifecycle="running", packets=self.active_packets())
        self.assert_silent(self.pretool("Write", {
            "file_path": str(self.task_dir / "log.txt"),
        }))

    def test_main_direct_state_file_write_blocked(self) -> None:
        self.write_state()
        self.assert_deny(
            self.pretool("Write", {
                "file_path": str(self.task_dir / "state.json"),
            }),
            "state_file_protection",
        )

    def test_worker_write_inside_allowed_paths_allowed(self) -> None:
        self.write_state(lifecycle="running", packets=self.active_packets())
        self.assert_silent(self.pretool(
            "Write", {"file_path": "src/foo/new.py"}, "dev-with-tdd"))
        self.assert_silent(self.pretool(
            "Write", {"file_path": "src/foo/deep/x.py"}, "dev-with-tdd"))

    def test_worker_write_outside_allowed_paths_blocked(self) -> None:
        self.write_state(lifecycle="running", packets=self.active_packets())
        self.assert_deny(
            self.pretool("Write", {"file_path": "src/bar/evil.py"},
                         "dev-with-tdd"),
            "worker_write_outside_packet",
        )

    def test_worker_write_prefix_boundary_blocked(self) -> None:
        self.write_state(lifecycle="running", packets=self.active_packets())
        self.assert_deny(
            self.pretool("Write", {"file_path": "src/foobar/evil.py"},
                         "dev-with-tdd"),
            "worker_write_outside_packet",
        )

    def test_worker_write_before_running_blocked(self) -> None:
        self.write_state(lifecycle="prepared", gate_status="passed",
                         packets=self.active_packets())
        self.assert_deny(
            self.pretool("Write", {"file_path": "src/foo/new.py"},
                         "dev-with-tdd"),
            "worker_write_outside_packet",
        )

    def test_bash_redirect_to_business_path_blocked(self) -> None:
        self.write_state(lifecycle="prepared", gate_status="passed")
        self.assert_deny(
            self.pretool("Bash", {"command": "echo x > src/foo/new.py"}),
            "coordinator_direct_write",
        )

    def test_bash_direct_state_file_write_blocked(self) -> None:
        self.write_state()
        self.assert_deny(
            self.pretool("Bash", {
                "command": "echo x > %s" % (self.task_dir / "state.json"),
            }),
            "state_file_protection",
        )

    def test_bash_git_commit_blocked(self) -> None:
        self.write_state(lifecycle="running", packets=self.active_packets())
        self.assert_deny(
            self.pretool("Bash", {"command": "git commit -m x"}),
            "git_owner_violation",
        )

    def test_bash_git_status_allowed(self) -> None:
        self.write_state(lifecycle="running", packets=self.active_packets())
        self.assert_silent(
            self.pretool("Bash", {"command": "git status --porcelain"}))

    def test_bash_git_other_repo_out_of_scope(self) -> None:
        self.write_state(lifecycle="running", packets=self.active_packets())
        self.assert_silent(self.pretool("Bash", {
            "command": "git -C /tmp/elsewhere commit -m x",
        }))

    def test_bash_runner_invocation_allowed(self) -> None:
        self.write_state(lifecycle="running", packets=self.active_packets())
        self.assert_silent(self.pretool("Bash", {
            "command": "%s state --show --project-root %s --task-id t1"
                       % (RUNNER, self.root),
        }))

    def test_agent_worker_dispatch_after_gate_allowed(self) -> None:
        self.write_state(lifecycle="prepared", gate_status="passed",
                         packets=self.active_packets())
        self.assert_silent(self.pretool("Agent", {
            "subagent_type": "dev-with-tdd",
            "prompt": "Required skill: dev-with-tdd",
        }))

    def test_agent_worker_dispatch_before_gate_blocked(self) -> None:
        self.write_state(lifecycle="approved")
        self.assert_deny(
            self.pretool("Agent", {
                "subagent_type": "dev-with-tdd",
                "prompt": "Required skill: dev-with-tdd",
            }),
            "dispatch_mode_mismatch",
        )

    def test_agent_worker_dispatch_without_state_blocked(self) -> None:
        self.assert_deny(
            self.pretool("Agent", {
                "subagent_type": "dev-with-tdd",
                "prompt": "Required skill: dev-with-tdd",
            }),
            "dispatch_mode_mismatch",
        )

    def test_agent_other_subagent_unaffected(self) -> None:
        self.write_state(lifecycle="approved")
        self.assert_silent(self.pretool("Agent", {
            "subagent_type": "Explore",
            "prompt": "search something",
        }))

    def test_corrupt_state_fails_closed(self) -> None:
        (self.task_dir / "state.json").write_text("{not json",
                                                  encoding="utf-8")
        self.assert_deny(
            self.pretool("Write", {"file_path": "src/x.py"}),
            "coordinator_direct_write",
        )

    def test_parallel_worktree_main_write_blocked(self) -> None:
        worktree = self.task_dir / "worktrees" / "P1"
        self.write_state(lifecycle="running", packets=self.active_packets(
            worktree=worktree))
        self.assert_deny(
            self.pretool("Write", {"file_path": str(worktree / "src/x.py")}),
            "coordinator_direct_write",
        )

    def test_parallel_worktree_worker_write_allowed(self) -> None:
        worktree = self.task_dir / "worktrees" / "P1"
        self.write_state(lifecycle="running", packets=self.active_packets(
            worktree=worktree))
        self.assert_silent(self.pretool(
            "Write", {"file_path": str(worktree / "src/foo/x.py")},
            "dev-with-tdd"))


class StopHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()
        self.task_dir = self.root / ".tmp" / "t1"
        self.task_dir.mkdir(parents=True)

    def write_state(self, lifecycle: str) -> None:
        data = {
            "schema_version": 1,
            "task_id": "t1",
            "project_root": str(self.root.resolve()),
            "task_directory": str(self.task_dir.resolve()),
            "created_at": "2026-07-31T00:00:00+00:00",
            "lifecycle": lifecycle,
            "gate": {"status": "pending", "blocked_reason": "none"},
            "versions": {"plan": "v1", "context": "v1", "task": "v1"},
            "packets": [],
            "worker": {"handle": None, "transport": None},
            "transitions": [],
        }
        (self.task_dir / "state.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    def stop(self) -> subprocess.CompletedProcess:
        return run_hook(STOP, {"cwd": str(self.root), "hook_event_name": "Stop"})

    def test_running_state_warns_once(self) -> None:
        self.write_state("running")

        first = self.stop()
        self.assertEqual(first.returncode, 0)
        self.assertIn("additionalContext", first.stdout)
        self.assertIn("running", first.stdout)
        marker = self.task_dir / ".stop-warned"
        self.assertEqual(marker.read_text(encoding="utf-8").strip(), "running")

        second = self.stop()
        self.assertEqual(second.stdout, "")

    def test_approved_never_dispatched_warns(self) -> None:
        self.write_state("approved")
        self.assertIn("additionalContext", self.stop().stdout)

    def test_terminal_state_silent(self) -> None:
        self.write_state("finalized")
        self.assertEqual(self.stop().stdout, "")

    def test_no_state_silent(self) -> None:
        self.assertEqual(self.stop().stdout, "")


class StateLibUnitTest(unittest.TestCase):
    def test_bash_write_targets_cp_uses_destination(self) -> None:
        sys.path.insert(0, str(HOOKS_DIR))
        from lib import state as S
        self.assertEqual(
            S.bash_write_targets("cp a.txt src/foo/"),
            ["src/foo/"],
        )
        self.assertEqual(
            S.bash_write_targets("mv b.txt src/foo/deep/"),
            ["src/foo/deep/"],
        )
        self.assertEqual(
            S.bash_write_targets("touch x && rm -rf y"),
            ["x", "y"],
        )
        self.assertEqual(
            S.bash_write_targets("printf x > out.txt"),
            ["out.txt"],
        )

    def test_git_subcommand_classification(self) -> None:
        sys.path.insert(0, str(HOOKS_DIR))
        from lib import state as S
        self.assertTrue(S.git_command_allowed("status", None))
        self.assertTrue(S.git_command_allowed("branch", "--show-current"))
        self.assertTrue(S.git_command_allowed("worktree", "list"))
        self.assertFalse(S.git_command_allowed("commit", None))
        self.assertFalse(S.git_command_allowed("branch", "-d"))
        self.assertFalse(S.git_command_allowed("worktree", "add"))
        self.assertFalse(S.git_command_allowed("config", "user.name"))
        self.assertTrue(S.git_command_allowed("config", "--get"))


if __name__ == "__main__":
    unittest.main()
