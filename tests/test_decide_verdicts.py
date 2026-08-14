from pathlib import Path
import subprocess
import tempfile
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / shared.MAIN_SKILL / "scripts" / shared.SCRIPT_DECIDE_VERDICTS


PASS_VERDICT = "verdict: PASS\n"
FAIL_VERDICT = (
    "[检查1] PASS\n"
    "[AC-1] FAIL\n"
    "证据: code/greeter.py:10 缺少边界处理\n"
    "理由: 断言要求返回空串\n"
    "verdict: FAIL\n"
)


class DecideVerdictsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp = Path(self.temp_dir.name)
        self.a = self.temp / "A.md"
        self.b = self.temp / "B.md"

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, check=False
        )

    def verdict_args(self) -> tuple:
        return (
            shared.FLAG_VERDICT_A, str(self.a),
            shared.FLAG_VERDICT_B, str(self.b),
        )

    def test_double_pass(self) -> None:
        self.a.write_text(PASS_VERDICT, encoding="utf-8")
        self.b.write_text(PASS_VERDICT, encoding="utf-8")

        result = self.run_script(*self.verdict_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertEqual(result.stdout.strip(), shared.DECIDE_DOUBLE_PASS)

    def test_double_fail(self) -> None:
        self.a.write_text(FAIL_VERDICT, encoding="utf-8")
        self.b.write_text(FAIL_VERDICT, encoding="utf-8")

        result = self.run_script(*self.verdict_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertEqual(result.stdout.strip(), shared.DECIDE_DOUBLE_FAIL)

    def test_split_pass_fail(self) -> None:
        self.a.write_text(PASS_VERDICT, encoding="utf-8")
        self.b.write_text(FAIL_VERDICT, encoding="utf-8")

        result = self.run_script(*self.verdict_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertEqual(result.stdout.strip(), shared.DECIDE_SPLIT)

    def test_split_fail_pass(self) -> None:
        self.a.write_text(FAIL_VERDICT, encoding="utf-8")
        self.b.write_text(PASS_VERDICT, encoding="utf-8")

        result = self.run_script(*self.verdict_args())

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertEqual(result.stdout.strip(), shared.DECIDE_SPLIT)

    def test_malformed_a_names_the_file(self) -> None:
        self.a.write_text("not a verdict\n", encoding="utf-8")
        self.b.write_text(PASS_VERDICT, encoding="utf-8")

        result = self.run_script(*self.verdict_args())

        self.assertEqual(result.returncode, shared.EXIT_USAGE)
        self.assertEqual(
            result.stdout.strip(),
            f"{shared.DECIDE_MALFORMED} ({self.a})",
        )

    def test_malformed_b_names_the_file(self) -> None:
        self.a.write_text(PASS_VERDICT, encoding="utf-8")
        self.b.write_text("", encoding="utf-8")

        result = self.run_script(*self.verdict_args())

        self.assertEqual(result.returncode, shared.EXIT_USAGE)
        self.assertEqual(
            result.stdout.strip(),
            f"{shared.DECIDE_MALFORMED} ({self.b})",
        )

    def test_missing_file_is_malformed(self) -> None:
        self.a.write_text(PASS_VERDICT, encoding="utf-8")
        # self.b never written.

        result = self.run_script(*self.verdict_args())

        self.assertEqual(result.returncode, shared.EXIT_USAGE)
        self.assertEqual(
            result.stdout.strip(),
            f"{shared.DECIDE_MALFORMED} ({self.b})",
        )

    def test_usage_errors_exit_two(self) -> None:
        self.a.write_text(PASS_VERDICT, encoding="utf-8")
        self.b.write_text(PASS_VERDICT, encoding="utf-8")
        cases = [
            (),
            (shared.FLAG_VERDICT_A, str(self.a)),
            (shared.FLAG_VERDICT_A, str(self.a),
             shared.FLAG_VERDICT_B, str(self.b), "--bogus"),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"args={args}\n{result.stdout}{result.stderr}")


if __name__ == "__main__":
    unittest.main()
