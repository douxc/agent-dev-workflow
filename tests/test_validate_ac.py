from pathlib import Path
import subprocess
import tempfile
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / shared.MAIN_SKILL / "scripts" / shared.SCRIPT_VALIDATE_AC


def write_scope(path: Path, files: tuple, infra: tuple = ()) -> None:
    lines = ["## 范围声明", "task: demo", "base: HEAD"]
    lines.append(shared.SCOPE_MARKER_FILES)
    lines += [f"- {item}" for item in files]
    lines.append(shared.SCOPE_MARKER_INFRA)
    lines += [f"- {item}" for item in infra]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ac(path: Path, items: tuple) -> None:
    """items: tuple of (number, assert_text, owner_csv, verify)."""
    lines = [shared.AC_HEADER, ""]
    for num, assertion, owner, verify in items:
        lines.append(f"- AC-{num}: behavior {num}")
        lines.append(f"  - 断言: {assertion}")
        lines.append(f"  - 归属: {owner}")
        lines.append(f"  - 验证: {verify}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class ValidateAcTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp = Path(self.temp_dir.name)
        self.ac = self.temp / "ac-list.md"
        self.scope = self.temp / "scope.md"

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, check=False
        )

    def default_args(self) -> tuple:
        return (
            shared.FLAG_PROJECT_ROOT, str(self.temp),
            shared.FLAG_AC_FILE, str(self.ac),
            shared.FLAG_SCOPE_FILE, str(self.scope),
        )

    def test_pass_for_well_formed_consistent_ac(self) -> None:
        write_scope(self.scope, ("src/greeter.py", "tests/test_greeter.py"))
        write_ac(self.ac, (
            (1, "hello('world') == 'hello, world'", "src/greeter.py", "unit"),
            (2, "test file imports greeter", "tests/test_greeter.py", "integration"),
        ))

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS, msg=result.stdout)
        self.assertIn(shared.AC_CHECK_PASS, result.stdout)
        last_line = result.stdout.rstrip().splitlines()[-1]
        self.assertTrue(last_line.startswith(shared.AC_CHECK_PASS),
                        msg=f"last line: {last_line!r}")

    def test_fail_when_verify_value_outside_enum(self) -> None:
        write_scope(self.scope, ("src/greeter.py",))
        write_ac(self.ac, (
            (1, "hello('world') == 'hello, world'", "src/greeter.py", "bogus"),
        ))

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.AC_CHECK_FAIL, result.stdout)
        self.assertIn("AC-1", result.stdout)

    def test_fail_when_assertion_has_banned_word(self) -> None:
        write_scope(self.scope, ("src/greeter.py",))
        write_ac(self.ac, (
            (1, "return value is 合理", "src/greeter.py", "unit"),
        ))

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.AC_CHECK_FAIL, result.stdout)

    def test_fail_when_owner_not_in_scope(self) -> None:
        write_scope(self.scope, ("src/greeter.py",))
        write_ac(self.ac, (
            (1, "hello('world') == 'hello, world'", "src/other.py", "unit"),
        ))

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.AC_CHECK_FAIL, result.stdout)

    def test_fail_when_scope_file_uncovered_by_any_ac(self) -> None:
        write_scope(self.scope, ("src/greeter.py", "src/orphan.py"))
        write_ac(self.ac, (
            (1, "hello('world') == 'hello, world'", "src/greeter.py", "unit"),
        ))

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.AC_CHECK_FAIL, result.stdout)
        self.assertIn("src/orphan.py", result.stdout)

    def test_fail_when_ac_missing_a_field(self) -> None:
        write_scope(self.scope, ("src/greeter.py",))
        # No 验证 line on AC-1.
        self.ac.write_text(
            f"{shared.AC_HEADER}\n\n- AC-1: behavior\n"
            "  - 断言: hello('world') == 'hello, world'\n"
            "  - 归属: src/greeter.py\n\n",
            encoding="utf-8",
        )

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.AC_CHECK_FAIL, result.stdout)

    def test_infra_file_need_not_be_covered_by_ac(self) -> None:
        write_scope(self.scope, ("src/greeter.py",), infra=("pyproject.toml",))
        write_ac(self.ac, (
            (1, "hello('world') == 'hello, world'", "src/greeter.py", "unit"),
        ))

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS, msg=result.stdout)

    def test_usage_errors_exit_two(self) -> None:
        write_scope(self.scope, ("src/greeter.py",))
        write_ac(self.ac, (
            (1, "hello('world') == 'hello, world'", "src/greeter.py", "unit"),
        ))
        cases = [
            (),
            (shared.FLAG_PROJECT_ROOT, str(self.temp),
             shared.FLAG_AC_FILE, str(self.ac)),
            (shared.FLAG_PROJECT_ROOT, str(self.temp),
             shared.FLAG_AC_FILE, str(self.temp / "nope.md"),
             shared.FLAG_SCOPE_FILE, str(self.scope)),
            (shared.FLAG_PROJECT_ROOT, str(self.temp),
             shared.FLAG_AC_FILE, str(self.ac),
             shared.FLAG_SCOPE_FILE, str(self.temp / "nope.md")),
            (shared.FLAG_PROJECT_ROOT, str(self.temp),
             shared.FLAG_AC_FILE, str(self.ac),
             shared.FLAG_SCOPE_FILE, str(self.scope), "--bogus"),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"args={args}\n{result.stdout}{result.stderr}")


if __name__ == "__main__":
    unittest.main()
