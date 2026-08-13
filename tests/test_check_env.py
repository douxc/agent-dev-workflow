from pathlib import Path
import subprocess
import tempfile
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / shared.MAIN_SKILL / "scripts" / shared.SCRIPT_CHECK_ENV


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=check
    )


class CheckEnvConstantsTest(unittest.TestCase):
    def test_shared_constants_for_new_scripts(self) -> None:
        expected = {
            "SCRIPT_CHECK_ENV": "check-env.sh",
            "SCRIPT_VALIDATE_AC": "validate-ac.sh",
            "SCRIPT_PARSE_VERDICT": "parse-verdict.sh",
            "FLAG_BRANCH": "--branch",
            "FLAG_AC_FILE": "--ac-file",
            "FLAG_VERDICT_FILE": "--verdict-file",
            "ENV_CHECK_PASS": "env-check: PASS",
            "ENV_CHECK_FAIL": "env-check: FAIL",
            "AC_CHECK_PASS": "ac-check: PASS",
            "AC_CHECK_FAIL": "ac-check: FAIL",
            "VERDICT_PARSE_PASS": "verdict-parse: PASS",
            "VERDICT_PARSE_FAIL": "verdict-parse: FAIL",
            "VERDICT_PARSE_MALFORMED": "verdict-parse: MALFORMED",
        }
        for name, value in expected.items():
            with self.subTest(name=name):
                self.assertTrue(hasattr(shared, name),
                                msg=f"shared.{name} missing")
                self.assertEqual(getattr(shared, name), value)


class CheckEnvTest(unittest.TestCase):
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
        self.task_branch = "task-feature"

    def checkout_task_branch(self) -> None:
        git(self.repo, "checkout", "-q", "-b", self.task_branch)

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, check=False
        )

    def default_args(self, base: str = None, branch: str = None) -> tuple:
        return (
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_BASE, base or self.base,
            shared.FLAG_BRANCH, branch or self.task_branch,
        )

    def test_pass_on_clean_task_branch_at_base(self) -> None:
        self.checkout_task_branch()
        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS, msg=result.stdout)
        self.assertIn(shared.ENV_CHECK_PASS, result.stdout)
        last_line = result.stdout.rstrip().splitlines()[-1]
        self.assertTrue(last_line.startswith(shared.ENV_CHECK_PASS),
                        msg=f"last line: {last_line!r}")

    def test_fail_when_current_branch_differs_from_declared(self) -> None:
        # Still on main while declaring a task branch.
        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.ENV_CHECK_FAIL, result.stdout)

    def test_fail_when_working_tree_has_non_tmp_change(self) -> None:
        self.checkout_task_branch()
        (self.repo / "stray.txt").write_text("stray\n", encoding="utf-8")

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.ENV_CHECK_FAIL, result.stdout)

    def test_tmp_only_changes_do_not_fail(self) -> None:
        self.checkout_task_branch()
        tmp_file = self.repo / ".tmp" / "pkg" / "scope.md"
        tmp_file.parent.mkdir(parents=True)
        tmp_file.write_text("## 范围声明\n", encoding="utf-8")

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS, msg=result.stdout)

    def test_fail_when_head_advanced_past_base(self) -> None:
        self.checkout_task_branch()
        (self.repo / "new.txt").write_text("new\n", encoding="utf-8")
        git(self.repo, "add", "new.txt")
        git(self.repo, "commit", "-qm", "advance")

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.ENV_CHECK_FAIL, result.stdout)

    def test_protected_branch_name_is_usage_error(self) -> None:
        self.checkout_task_branch()
        for protected in ("main", "master"):
            with self.subTest(branch=protected):
                result = self.run_script(*self.default_args(branch=protected))

                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"{protected}\n{result.stdout}{result.stderr}")

    def test_usage_errors_exit_two(self) -> None:
        self.checkout_task_branch()
        non_git = self.temp / "non-git"
        non_git.mkdir()
        cases = [
            (),
            (shared.FLAG_PROJECT_ROOT,),
            (shared.FLAG_PROJECT_ROOT, str(non_git),
             shared.FLAG_BASE, self.base,
             shared.FLAG_BRANCH, self.task_branch),
            (shared.FLAG_PROJECT_ROOT, str(self.repo),
             shared.FLAG_BASE, "not-a-rev",
             shared.FLAG_BRANCH, self.task_branch),
            (shared.FLAG_PROJECT_ROOT, str(self.repo),
             shared.FLAG_BASE, self.base,
             shared.FLAG_BRANCH, self.task_branch, "--bogus"),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"args={args}\n{result.stdout}{result.stderr}")


if __name__ == "__main__":
    unittest.main()
