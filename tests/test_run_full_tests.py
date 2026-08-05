from pathlib import Path
import subprocess
import tempfile
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / shared.MAIN_SKILL / "scripts" / shared.SCRIPT_RUN_FULL_TESTS


class RunFullTestsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp = Path(self.temp_dir.name)
        self.project = self.temp / "project"
        self.project.mkdir()

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, check=False
        )

    def base_args(self, test_cmd: str) -> tuple:
        return (
            shared.FLAG_PROJECT_ROOT, str(self.project),
            shared.FLAG_TEST_CMD, test_cmd,
        )

    def test_passing_command_exits_zero(self) -> None:
        result = self.run_script(*self.base_args("python3 -c 'print(\"ok\")'"))
        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn(shared.RUN_FULL_TESTS_PASS, result.stdout)
        self.assertTrue(result.stdout.rstrip().endswith(
            shared.RUN_FULL_TESTS_PASS))

    def test_failing_command_exits_one(self) -> None:
        result = self.run_script(*self.base_args("python3 -c 'exit(1)'"))
        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.RUN_FULL_TESTS_FAIL, result.stdout)
        self.assertIn("(exit 1)", result.stdout)

    def test_command_not_found_exits_one(self) -> None:
        result = self.run_script(*self.base_args("definitely-not-a-cmd-xyz"))
        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.RUN_FULL_TESTS_FAIL, result.stdout)

    def test_usage_errors_exit_two(self) -> None:
        cases = [
            (),
            (shared.FLAG_PROJECT_ROOT,),
            (shared.FLAG_PROJECT_ROOT, str(self.project)),
            (shared.FLAG_PROJECT_ROOT, str(self.temp / "missing"),
             shared.FLAG_TEST_CMD, "true"),
            (shared.FLAG_PROJECT_ROOT, str(self.project),
             shared.FLAG_TEST_CMD, "true",
             shared.FLAG_WORKDIR, str(self.temp / "missing")),
            (shared.FLAG_PROJECT_ROOT, str(self.project),
             shared.FLAG_TEST_CMD, "true",
             shared.FLAG_LOG_FILE, str(self.temp / "missing" / "log.txt")),
            (shared.FLAG_PROJECT_ROOT, str(self.project),
             shared.FLAG_TEST_CMD, "true", "--bogus"),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"args={args}\n{result.stdout}{result.stderr}")
                self.assertIn(shared.RUN_FULL_TESTS_USAGE, result.stdout)

    def test_workdir_is_honored(self) -> None:
        workdir = (self.temp / "workdir").resolve()
        workdir.mkdir()
        cmd = ("python3 -c 'import os; assert os.getcwd() == \"%s\", os.getcwd()'"
               % workdir)
        result = self.run_script(
            shared.FLAG_PROJECT_ROOT, str(self.project),
            shared.FLAG_TEST_CMD, cmd,
            shared.FLAG_WORKDIR, str(workdir),
        )
        self.assertEqual(result.returncode, shared.EXIT_PASS)

    def test_relative_log_file_is_resolved_from_project_root(self) -> None:
        workdir = self.temp / "workdir"
        workdir.mkdir()
        project_log_dir = self.project / "logs"
        project_log_dir.mkdir()
        project_log = project_log_dir / "full-tests.log"

        result = self.run_script(
            shared.FLAG_PROJECT_ROOT, str(self.project),
            shared.FLAG_TEST_CMD, "printf 'relative log\\n'",
            shared.FLAG_WORKDIR, str(workdir),
            shared.FLAG_LOG_FILE, "logs/full-tests.log",
        )

        self.assertEqual(
            result.returncode,
            shared.EXIT_PASS,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertEqual(project_log.read_text(encoding="utf-8"),
                         "relative log\n")
        self.assertFalse((workdir / "logs" / "full-tests.log").exists())

    def test_log_file_captures_output_and_status_is_last(self) -> None:
        log_file = self.temp / "log" / "full-tests.log"
        log_file.parent.mkdir()
        result = self.run_script(
            shared.FLAG_PROJECT_ROOT, str(self.project),
            shared.FLAG_TEST_CMD, "printf 'hello from tests\\n'",
            shared.FLAG_LOG_FILE, str(log_file),
        )
        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn("hello from tests", log_file.read_text(encoding="utf-8"))
        # Console output equals log content plus the status line.
        self.assertEqual(
            result.stdout,
            log_file.read_text(encoding="utf-8")
            + shared.RUN_FULL_TESTS_PASS + "\n",
        )

    def test_compound_command_via_sh(self) -> None:
        result = self.run_script(
            *self.base_args("python3 -c 'print(1)' && python3 -c 'print(2)'"))
        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn("1", result.stdout)
        self.assertIn("2", result.stdout)


if __name__ == "__main__":
    unittest.main()
