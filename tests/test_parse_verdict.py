from pathlib import Path
import subprocess
import tempfile
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / shared.MAIN_SKILL / "scripts" / shared.SCRIPT_PARSE_VERDICT


class ParseVerdictTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp = Path(self.temp_dir.name)

    def write_verdict(self, name: str, content: str) -> Path:
        path = self.temp / name
        path.write_text(content, encoding="utf-8")
        return path

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, check=False
        )

    def args(self, path: Path) -> tuple:
        return (shared.FLAG_VERDICT_FILE, str(path))

    def test_pass_verdict_exits_zero(self) -> None:
        path = self.write_verdict("A.md", (
            "[AC-1] PASS\n"
            "证据: code/src/greeter.py:5 hello\n\n"
            "verdict: PASS\n"
        ))

        result = self.run_script(*self.args(path))

        self.assertEqual(result.returncode, shared.EXIT_PASS, msg=result.stdout)
        self.assertIn(shared.VERDICT_PARSE_PASS, result.stdout)

    def test_fail_verdict_exits_one_with_fail_blocks(self) -> None:
        path = self.write_verdict("B.md", (
            "[AC-1] PASS\n"
            "证据: code/src/greeter.py:5 hello\n\n"
            "[AC-2] FAIL\n"
            "证据: code/tests/test_cli.py:5-9 only mock\n"
            "理由: island test\n\n"
            "[检查4] PASS\n"
            "证据: code/src/greeter.py:5-8\n\n"
            "verdict: FAIL\n"
        ))

        result = self.run_script(*self.args(path))

        self.assertEqual(result.returncode, shared.EXIT_FAIL, msg=result.stdout)
        self.assertIn(shared.VERDICT_PARSE_FAIL, result.stdout)
        self.assertIn("[AC-2]", result.stdout)
        self.assertIn("理由: island test", result.stdout)
        # PASS blocks are not echoed as failures.
        self.assertNotIn("[AC-1]", result.stdout)

    def test_malformed_verdict_exits_two(self) -> None:
        cases = {
            "散文末行": "[AC-1] PASS\n证据: code/x.py:1\n\nthis is not a verdict\n",
            "空文件": "",
            "无verdict行": "[AC-1] PASS\n证据: code/x.py:1\n",
        }
        for name, content in cases.items():
            with self.subTest(name=name):
                path = self.write_verdict(f"{name}.md", content)
                result = self.run_script(*self.args(path))
                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"{name}\n{result.stdout}{result.stderr}")

    def test_missing_file_exits_two(self) -> None:
        result = self.run_script(
            shared.FLAG_VERDICT_FILE, str(self.temp / "absent.md")
        )

        self.assertEqual(result.returncode, shared.EXIT_USAGE,
                         msg=result.stdout + result.stderr)

    def test_missing_argument_exits_two(self) -> None:
        result = self.run_script()

        self.assertEqual(result.returncode, shared.EXIT_USAGE,
                         msg=result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
