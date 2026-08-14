from pathlib import Path
import subprocess
import tempfile
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / shared.MAIN_SKILL / "scripts" / shared.SCRIPT_STAGE_SCOPE


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=check
    )


def write_scope(path: Path, files: tuple, infra: tuple = ()) -> None:
    lines = ["## 范围声明", "task: demo", "base: HEAD"]
    lines.append(shared.SCOPE_MARKER_FILES)
    lines += [f"- {item}" for item in files]
    lines.append(shared.SCOPE_MARKER_INFRA)
    lines += [f"- {item}" for item in infra]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class StageScopeTest(unittest.TestCase):
    """Fixture mirrors the real flow: feature branch, package under .tmp/,
    full-tests.log written by the §9 gate run, scope declared up front."""

    BRANCH = "feature/demo"

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp = Path(self.temp_dir.name)
        self.repo = self.temp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "--initial-branch=main")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "user.email", "t@example.com")
        (self.repo / "tracked.txt").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", "tracked.txt")
        git(self.repo, "commit", "-qm", "init")
        self.base = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        git(self.repo, "checkout", "-qb", self.BRANCH)
        # Package under .tmp/: excluded from the changed set and the clean
        # recheck, exactly like the real flow.
        self.task = self.repo / ".tmp" / "t1"
        self.package = self.task / "package"
        self.package.mkdir(parents=True)
        write_scope(self.package / "scope.md", ("tracked.txt", "src/new.txt"))
        (self.package / "test-command.txt").write_text(
            "python3 -m unittest\n", encoding="utf-8")
        self.log = self.task / "full-tests.log"
        self.log.write_text("...output...\nrun-full-tests: PASS\n", encoding="utf-8")
        # Declared changes on disk.
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "new.txt").write_text("new\n", encoding="utf-8")

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, check=False
        )

    def default_args(self) -> tuple:
        return (
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_PACKAGE, str(self.package),
            shared.FLAG_BASE, self.base,
            shared.FLAG_BRANCH, self.BRANCH,
            shared.FLAG_MESSAGE, "task: demo",
        )

    def committed_files(self) -> set:
        out = git(self.repo, "show", "--pretty=format:", "--name-only",
                  "HEAD").stdout
        return {line for line in out.splitlines() if line.strip()}

    def test_pass_commits_declared_changes_once(self) -> None:
        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS,
                         msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        self.assertIn(f"{shared.STAGE_SCOPE_PASS} (commit ", result.stdout)
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s").stdout.strip(),
                         "task: demo")
        self.assertEqual(self.committed_files(), {"tracked.txt", "src/new.txt"})
        # Exactly one commit after base.
        self.assertEqual(git(self.repo, "rev-list", "--count", f"{self.base}..HEAD")
                         .stdout.strip(), "1")
        # Clean tree apart from .tmp/.
        porcelain = git(self.repo, "status", "--porcelain").stdout
        self.assertTrue(
            all(line.startswith("?? .tmp/") for line in porcelain.splitlines()),
            msg=f"porcelain:\n{porcelain}",
        )

    def test_skip_mode_passes_without_test_log(self) -> None:
        self.log.unlink()
        (self.package / "test-command.txt").write_text("SKIP\n", encoding="utf-8")

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn(shared.STAGE_SCOPE_SKIP, result.stdout)
        self.assertEqual(self.committed_files(), {"tracked.txt", "src/new.txt"})

    def test_refuses_protected_main_branch(self) -> None:
        git(self.repo, "checkout", "-q", "main")
        result = self.run_script(
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_PACKAGE, str(self.package),
            shared.FLAG_BASE, self.base,
            shared.FLAG_BRANCH, "main",
            shared.FLAG_MESSAGE, "task: demo",
        )

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.STAGE_SCOPE_FAIL, result.stdout)
        self.assertIn("protected branch", result.stdout)

    def test_wrong_branch_fails(self) -> None:
        result = self.run_script(
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_PACKAGE, str(self.package),
            shared.FLAG_BASE, self.base,
            shared.FLAG_BRANCH, "feature/other",
            shared.FLAG_MESSAGE, "task: demo",
        )
        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn("!= expected feature/other", result.stdout)

    def test_head_mismatch_fails(self) -> None:
        git(self.repo, "commit", "-qam", "unexpected extra commit")
        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn("HEAD != base", result.stdout)

    def test_scope_recheck_fails_on_undeclared_file(self) -> None:
        (self.repo / "evil.txt").write_text("evil\n", encoding="utf-8")
        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.STAGE_SCOPE_FAIL, result.stdout)
        self.assertIn("scope recheck failed", result.stdout)

    def test_test_gate_requires_pass_log(self) -> None:
        self.log.unlink()
        result = self.run_script(*self.default_args())
        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn("full-tests.log missing", result.stdout)

        self.log.write_text("run-full-tests: FAIL (exit 1)\n", encoding="utf-8")
        result = self.run_script(*self.default_args())
        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn("test gate failed", result.stdout)

    def test_staged_set_mismatch_fails(self) -> None:
        # A file staged but absent from the working tree is invisible to the
        # changed-set computation yet present in the index: the staged ==
        # changed verification must catch it.
        (self.repo / "ghost.txt").write_text("ghost\n", encoding="utf-8")
        git(self.repo, "add", "ghost.txt")
        (self.repo / "ghost.txt").unlink()

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn("staged set != changed set", result.stdout)

    def test_usage_errors_exit_two(self) -> None:
        cases = [
            (),
            (shared.FLAG_PROJECT_ROOT, str(self.repo)),
            (shared.FLAG_PROJECT_ROOT, str(self.repo),
             shared.FLAG_PACKAGE, str(self.package)),
            (shared.FLAG_PROJECT_ROOT, str(self.repo),
             shared.FLAG_PACKAGE, str(self.package),
             shared.FLAG_BASE, self.base,
             shared.FLAG_BRANCH, self.BRANCH),
            (shared.FLAG_PROJECT_ROOT, str(self.repo),
             shared.FLAG_PACKAGE, str(self.package),
             shared.FLAG_BASE, self.base,
             shared.FLAG_BRANCH, self.BRANCH,
             shared.FLAG_MESSAGE, "msg", "--bogus"),
            (shared.FLAG_PROJECT_ROOT, str(self.repo),
             shared.FLAG_PACKAGE, str(self.temp / "no-such-package"),
             shared.FLAG_BASE, self.base,
             shared.FLAG_BRANCH, self.BRANCH,
             shared.FLAG_MESSAGE, "msg"),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"args={args}\n{result.stdout}{result.stderr}")


if __name__ == "__main__":
    unittest.main()
