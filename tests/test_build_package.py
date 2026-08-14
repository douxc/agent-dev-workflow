from pathlib import Path
import subprocess
import tempfile
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / shared.MAIN_SKILL / "scripts" / shared.SCRIPT_BUILD_PACKAGE


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=check
    )


class BuildPackageTest(unittest.TestCase):
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
        # The package lives under .tmp/ in the real flow; .tmp paths are
        # unconditionally excluded by the changed-set computation.
        self.package = self.repo / ".tmp" / "t1" / "package"
        self.package.mkdir(parents=True)

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, check=False
        )

    def default_args(self) -> tuple:
        return (
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_PACKAGE, str(self.package),
            shared.FLAG_BASE, self.base,
        )

    def test_builds_diff_and_code(self) -> None:
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "new.txt").write_text("new content\n", encoding="utf-8")

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn("build-package: PASS (2 files, 1 new)", result.stdout)
        diff = (self.package / "diff.txt").read_text(encoding="utf-8")
        self.assertIn("diff --git a/tracked.txt b/tracked.txt", diff)
        self.assertIn(f"{shared.NEW_FILE_MARKER}src/new.txt ==", diff)
        self.assertIn("new content", diff)
        self.assertEqual(
            (self.package / "code" / "tracked.txt").read_text(encoding="utf-8"),
            "modified\n",
        )
        self.assertEqual(
            (self.package / "code" / "src" / "new.txt").read_text(
                encoding="utf-8"),
            "new content\n",
        )

    def test_project_map_excluded_from_code_and_diff(self) -> None:
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")
        (self.repo / "project-map.md").write_text("# project-map\n", encoding="utf-8")

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn("build-package: PASS (1 files, 0 new)", result.stdout)
        self.assertFalse((self.package / "code" / "project-map.md").exists())
        self.assertNotIn("project-map.md",
                         (self.package / "diff.txt").read_text(encoding="utf-8"))

    def test_deleted_tracked_file_has_no_copy(self) -> None:
        (self.repo / "tracked.txt").unlink()

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn("build-package: PASS (1 files, 0 new)", result.stdout)
        diff = (self.package / "diff.txt").read_text(encoding="utf-8")
        self.assertIn("deleted file mode", diff)
        self.assertFalse((self.package / "code" / "tracked.txt").exists())

    def test_tmp_changes_never_enter_package(self) -> None:
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")
        junk = self.repo / ".tmp" / "t1" / "junk.txt"
        junk.write_text("junk\n", encoding="utf-8")

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertFalse((self.package / "code" / ".tmp").exists())
        self.assertNotIn("junk.txt",
                         (self.package / "diff.txt").read_text(encoding="utf-8"))

    def test_unicode_space_and_tab_path_copied_exactly(self) -> None:
        unusual = "中文 file\tname.txt"
        (self.repo / unusual).write_text("new\n", encoding="utf-8")

        result = self.run_script(*self.default_args())

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn(f"{shared.NEW_FILE_MARKER}{unusual} ==",
                      (self.package / "diff.txt").read_text(encoding="utf-8"))
        self.assertEqual(
            (self.package / "code" / unusual).read_text(encoding="utf-8"),
            "new\n",
        )

    def test_usage_errors_exit_two(self) -> None:
        cases = [
            (),
            (shared.FLAG_PROJECT_ROOT,),
            (shared.FLAG_PROJECT_ROOT, str(self.repo)),
            (shared.FLAG_PROJECT_ROOT, str(self.temp / "missing"),
             shared.FLAG_PACKAGE, str(self.package)),
            (shared.FLAG_PROJECT_ROOT, str(self.repo),
             shared.FLAG_PACKAGE, str(self.temp / "no-such-package")),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"args={args}\n{result.stdout}{result.stderr}")

    def test_changed_set_read_failure_exits_one(self) -> None:
        # A missing base revision makes check-scope --list-changed fail.
        result = self.run_script(
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_PACKAGE, str(self.package),
            shared.FLAG_BASE, "not-a-rev",
        )
        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(shared.BUILD_PACKAGE_FAIL, result.stdout)


if __name__ == "__main__":
    unittest.main()
