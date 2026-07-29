from pathlib import Path
import json
import os
import subprocess
import tempfile
from typing import Optional
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "git-workflow.sh"


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


class GitWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp = Path(self.temp_dir.name)
        self.remote = self.temp / "remote.git"
        self.seed = self.temp / "seed"
        self.project = self.temp / "project"
        self.peer = self.temp / "peer"

        git(self.temp, "init", "--bare", "--initial-branch=main", str(self.remote))
        git(self.temp, "init", "--initial-branch=main", str(self.seed))
        self.configure(self.seed)
        (self.seed / ".gitignore").write_text(
            "/.tmp/\n/node_modules/\n", encoding="utf-8"
        )
        (self.seed / "tracked.txt").write_text("initial\n", encoding="utf-8")
        git(self.seed, "add", ".gitignore", "tracked.txt")
        git(self.seed, "commit", "-m", "initial")
        git(self.seed, "remote", "add", "origin", str(self.remote))
        git(self.seed, "push", "-u", "origin", "main")

        git(self.temp, "clone", str(self.remote), str(self.project))
        git(self.temp, "clone", str(self.remote), str(self.peer))
        self.configure(self.project)
        self.configure(self.peer)
        self.base = git(self.project, "rev-parse", "HEAD").stdout.strip()

    def configure(self, repo: Path) -> None:
        git(repo, "config", "user.name", "Test User")
        git(repo, "config", "user.email", "test@example.com")

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

    def peer_commit(self, name: str = "peer.txt", branch: str = "main") -> str:
        git(self.peer, "switch", branch)
        path = self.peer / name
        path.write_text(f"{name}\n", encoding="utf-8")
        git(self.peer, "add", name)
        git(self.peer, "commit", "-m", f"add {name}")
        git(self.peer, "push", "origin", branch)
        return git(self.peer, "rev-parse", "HEAD").stdout.strip()

    def test_script_exists_is_executable_and_has_valid_shell_syntax(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK))
        result = subprocess.run(
            ["sh", "-n", str(SCRIPT)], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_inspect_emits_stable_tab_separated_state(self) -> None:
        result = self.run_script("inspect", "--project-root", str(self.project))
        self.assert_success(result)
        rows = [line.split("\t", 1) for line in result.stdout.splitlines()]
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == 2 for row in rows))
        values = dict(row for row in rows if row[0] != "worktree")
        self.assertEqual(values["project_root"], str(self.project.resolve()))
        self.assertEqual(values["remote"], "origin")
        self.assertEqual(values["default_branch"], "main")
        self.assertEqual(values["current_branch"], "main")
        self.assertEqual(values["head"], self.base)
        self.assertEqual(values["clean"], "yes")
        self.assertEqual(values["operation"], "none")
        self.assertIn("worktree", [row[0] for row in rows])

    def test_sync_fetches_and_fast_forwards_default_branch(self) -> None:
        expected = self.peer_commit()
        result = self.run_script(
            "sync",
            "--project-root",
            str(self.project),
            "--remote",
            "origin",
            "--fetch-source",
            str(self.remote),
        )
        self.assert_success(result)
        self.assertIn(f"base_sha\t{expected}\n", result.stdout)
        self.assertEqual(git(self.project, "rev-parse", "HEAD").stdout.strip(), expected)
        self.assertEqual(
            git(self.project, "remote", "get-url", "origin").stdout.strip(),
            str(self.remote),
        )

    def test_sync_rejects_dirty_ahead_and_diverged_default_branch(self) -> None:
        (self.project / "tracked.txt").write_text("dirty\n", encoding="utf-8")
        dirty = self.run_script("sync", "--project-root", str(self.project))
        self.assertNotEqual(dirty.returncode, 0)
        self.assertIn("clean", dirty.stderr)

        git(self.project, "restore", "tracked.txt")
        (self.project / "local.txt").write_text("local\n", encoding="utf-8")
        git(self.project, "add", "local.txt")
        git(self.project, "commit", "-m", "local ahead")
        ahead = self.run_script("sync", "--project-root", str(self.project))
        self.assertNotEqual(ahead.returncode, 0)
        self.assertIn("ahead", ahead.stderr)

        self.peer_commit()
        diverged = self.run_script("sync", "--project-root", str(self.project))
        self.assertNotEqual(diverged.returncode, 0)
        self.assertIn("diverged", diverged.stderr)

    def test_sync_rejects_detached_head_and_in_progress_operation(self) -> None:
        git(self.project, "switch", "--detach")
        detached = self.run_script("sync", "--project-root", str(self.project))
        self.assertNotEqual(detached.returncode, 0)
        self.assertIn("detached", detached.stderr)

        git(self.project, "switch", "main")
        merge_head = Path(
            git(self.project, "rev-parse", "--git-path", "MERGE_HEAD").stdout.strip()
        )
        if not merge_head.is_absolute():
            merge_head = self.project / merge_head
        merge_head.write_text(f"{self.base}\n", encoding="utf-8")
        in_progress = self.run_script("sync", "--project-root", str(self.project))
        self.assertNotEqual(in_progress.returncode, 0)
        self.assertIn("operation in progress", in_progress.stderr)

    def test_prepare_serial_uses_current_worktree_without_adding_one(self) -> None:
        before = git(self.project, "worktree", "list", "--porcelain").stdout.count(
            "worktree "
        )
        result = self.run_script(
            "prepare-serial",
            "--project-root",
            str(self.project),
            "--base",
            self.base,
            "--branch",
            "task/serial",
        )
        self.assert_success(result)
        after = git(self.project, "worktree", "list", "--porcelain").stdout.count(
            "worktree "
        )
        self.assertEqual(before, after)
        self.assertEqual(
            git(self.project, "branch", "--show-current").stdout.strip(),
            "task/serial",
        )
        self.assertEqual(git(self.project, "rev-parse", "HEAD").stdout.strip(), self.base)

    def test_prepare_parallel_uses_same_base_and_links_safe_dependency(self) -> None:
        task_dir = self.make_owner()
        dependency = self.project / "node_modules"
        dependency.mkdir()
        (dependency / "marker").write_text("shared\n", encoding="utf-8")

        for packet in ("packet-a", "packet-b"):
            result = self.run_script(
                "prepare-parallel",
                "--project-root",
                str(self.project),
                "--task-id",
                "task-one",
                "--packet-id",
                packet,
                "--base",
                self.base,
                "--branch",
                f"task/{packet}",
                "--share",
                "node_modules",
            )
            self.assert_success(result)
            worktree = task_dir / "worktrees" / packet
            self.assertEqual(
                git(worktree, "rev-parse", "HEAD").stdout.strip(), self.base
            )
            self.assertTrue((worktree / "node_modules").is_symlink())
            self.assertEqual(
                (worktree / "node_modules").resolve(), dependency.resolve()
            )

    def test_prepare_parallel_rejects_path_escape_and_command_injection(self) -> None:
        self.make_owner()
        cases = (
            ("--packet-id", "../escape"),
            ("--task-id", "task;touch-pwned"),
            ("--branch", "task/a;touch-pwned"),
            ("--share", "../node_modules"),
            ("--share", "node_*"),
        )
        for flag, value in cases:
            with self.subTest(flag=flag, value=value):
                args = [
                    "prepare-parallel",
                    "--project-root",
                    str(self.project),
                    "--task-id",
                    "task-one",
                    "--packet-id",
                    "packet-a",
                    "--base",
                    self.base,
                    "--branch",
                    "task/packet-a",
                ]
                index = args.index(flag) if flag in args else -1
                if index >= 0:
                    args[index + 1] = value
                else:
                    args.extend((flag, value))
                result = self.run_script(*args)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.temp / "escape").exists())
        self.assertFalse((self.project / "pwned").exists())

    def test_verify_requires_exact_context_and_clean_operation_state(self) -> None:
        ok = self.run_script(
            "verify",
            "--project-root",
            str(self.project),
            "--worktree",
            str(self.project),
            "--branch",
            "main",
            "--base",
            self.base,
            "--require-clean",
        )
        self.assert_success(ok)
        wrong = self.run_script(
            "verify",
            "--project-root",
            str(self.project),
            "--worktree",
            str(self.project),
            "--branch",
            "task/wrong",
            "--base",
            self.base,
        )
        self.assertNotEqual(wrong.returncode, 0)

    def test_commit_stages_only_explicit_authorized_paths(self) -> None:
        serial = self.run_script(
            "prepare-serial",
            "--project-root",
            str(self.project),
            "--base",
            self.base,
            "--branch",
            "task/commit",
        )
        self.assert_success(serial)
        (self.project / "allowed.txt").write_text("allowed\n", encoding="utf-8")
        (self.project / "other.txt").write_text("other\n", encoding="utf-8")
        result = self.run_script(
            "commit",
            "--project-root",
            str(self.project),
            "--worktree",
            str(self.project),
            "--branch",
            "task/commit",
            "--base",
            self.base,
            "--message",
            "feat: allowed",
            "--path",
            "allowed.txt",
        )
        self.assert_success(result)
        self.assertEqual(
            git(self.project, "show", "--format=", "--name-only", "HEAD").stdout.strip(),
            "allowed.txt",
        )
        self.assertIn("?? other.txt", git(self.project, "status", "--short").stdout)

        invalid = self.run_script(
            "commit",
            "--project-root",
            str(self.project),
            "--worktree",
            str(self.project),
            "--branch",
            "task/commit",
            "--base",
            self.base,
            "--message",
            "invalid",
            "--path",
            "*.txt",
        )
        self.assertNotEqual(invalid.returncode, 0)

    def test_push_rejects_default_branch_and_non_fast_forward(self) -> None:
        default_push = self.run_script(
            "push",
            "--project-root",
            str(self.project),
            "--worktree",
            str(self.project),
            "--remote",
            "origin",
            "--default-branch",
            "main",
            "--expected-remote-tip",
            self.base,
        )
        self.assertNotEqual(default_push.returncode, 0)
        self.assertIn("default branch", default_push.stderr)

        git(self.project, "switch", "-c", "task/push", self.base)
        (self.project / "local.txt").write_text("local\n", encoding="utf-8")
        git(self.project, "add", "local.txt")
        git(self.project, "commit", "-m", "local")
        first = self.run_script(
            "push",
            "--project-root",
            str(self.project),
            "--worktree",
            str(self.project),
            "--remote",
            "origin",
            "--default-branch",
            "main",
            "--expected-remote-tip",
            "absent",
        )
        self.assert_success(first)

        git(self.peer, "fetch", "origin")
        git(self.peer, "switch", "-c", "task/push", "--track", "origin/task/push")
        remote_tip = self.peer_commit("peer-branch.txt", "task/push")
        (self.project / "local-two.txt").write_text("local two\n", encoding="utf-8")
        git(self.project, "add", "local-two.txt")
        git(self.project, "commit", "-m", "local two")
        rejected = self.run_script(
            "push",
            "--project-root",
            str(self.project),
            "--worktree",
            str(self.project),
            "--remote",
            "origin",
            "--default-branch",
            "main",
            "--expected-remote-tip",
            remote_tip,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("fast-forward", rejected.stderr)

    def test_cleanup_parallel_only_removes_matching_owned_clean_worktree(self) -> None:
        task_dir = self.make_owner()
        dependency = self.project / "node_modules"
        dependency.mkdir()
        prepared = self.run_script(
            "prepare-parallel",
            "--project-root",
            str(self.project),
            "--task-id",
            "task-one",
            "--packet-id",
            "packet-a",
            "--base",
            self.base,
            "--branch",
            "task/packet-a",
            "--share",
            "node_modules",
        )
        self.assert_success(prepared)
        worktree = task_dir / "worktrees" / "packet-a"
        (worktree / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        dirty = self.run_script(
            "cleanup-parallel",
            "--project-root",
            str(self.project),
            "--task-id",
            "task-one",
            "--packet-id",
            "packet-a",
            "--branch",
            "task/packet-a",
        )
        self.assertNotEqual(dirty.returncode, 0)
        self.assertTrue(worktree.exists())
        (worktree / "dirty.txt").unlink()

        cleaned = self.run_script(
            "cleanup-parallel",
            "--project-root",
            str(self.project),
            "--task-id",
            "task-one",
            "--packet-id",
            "packet-a",
            "--branch",
            "task/packet-a",
        )
        self.assert_success(cleaned)
        self.assertFalse(worktree.exists())
        self.assertEqual(
            git(self.project, "show-ref", "--verify", "refs/heads/task/packet-a").returncode,
            0,
        )

        other = self.make_owner("other-task")
        (other / "task-owner.json").write_text("{}", encoding="utf-8")
        rejected = self.run_script(
            "cleanup-parallel",
            "--project-root",
            str(self.project),
            "--task-id",
            "other-task",
            "--packet-id",
            "packet-z",
            "--branch",
            "task/packet-z",
        )
        self.assertNotEqual(rejected.returncode, 0)


if __name__ == "__main__":
    unittest.main()
