from pathlib import Path
import subprocess
import tempfile
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / shared.MAIN_SKILL / "scripts" / shared.SCRIPT_CHECK_SCOPE


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


class CheckScopeListChangedTest(unittest.TestCase):
    """--list-changed data mode: NUL records, no status line, exit 0/2."""

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

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, check=False
        )

    def list_args(self) -> tuple:
        return (
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_BASE, self.base,
            shared.FLAG_LIST_CHANGED,
        )

    def records(self, result: subprocess.CompletedProcess) -> set:
        self.assertEqual(result.returncode, shared.EXIT_PASS,
                         msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return {r for r in result.stdout.split("\0") if r}

    def test_emits_tracked_and_new_records_nul_delimited(self) -> None:
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "new.txt").write_text("new\n", encoding="utf-8")

        result = self.run_script(*self.list_args())

        self.assertEqual(
            self.records(result),
            {f"{shared.CHANGED_TRACKED}tracked.txt",
             f"{shared.CHANGED_NEW}src/new.txt"},
        )

    def test_emits_no_status_line_in_data_mode(self) -> None:
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")
        result = self.run_script(*self.list_args())
        self.assertEqual(result.stdout.rstrip("\0"), f"{shared.CHANGED_TRACKED}tracked.txt")

    def test_tmp_paths_excluded(self) -> None:
        (self.repo / ".tmp" / "x" / "junk.txt").parent.mkdir(parents=True)
        (self.repo / ".tmp" / "x" / "junk.txt").write_text("junk\n", encoding="utf-8")
        result = self.run_script(*self.list_args())
        self.assertEqual(self.records(result), set())

    def test_unicode_space_and_tab_path_preserved(self) -> None:
        unusual = "中文 file\tname.txt"
        (self.repo / unusual).write_text("new\n", encoding="utf-8")
        result = self.run_script(*self.list_args())
        self.assertEqual(self.records(result), {f"{shared.CHANGED_NEW}{unusual}"})

    def test_base_override_marks_later_commit_as_tracked(self) -> None:
        (self.repo / "added-later.txt").write_text("new\n", encoding="utf-8")
        git(self.repo, "add", "added-later.txt")
        git(self.repo, "commit", "-qm", "second")
        result = self.run_script(*self.list_args())
        self.assertEqual(self.records(result),
                         {f"{shared.CHANGED_TRACKED}added-later.txt"})

    def test_list_changed_exclusive_with_scope_file(self) -> None:
        result = self.run_script(
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_SCOPE_FILE, str(self.repo / "scope.md"),
            shared.FLAG_BASE, self.base,
            shared.FLAG_LIST_CHANGED,
        )
        self.assertEqual(result.returncode, shared.EXIT_USAGE)

    def test_usage_errors_exit_two(self) -> None:
        cases = [
            (),
            (shared.FLAG_PROJECT_ROOT, str(self.repo)),
            (shared.FLAG_PROJECT_ROOT, str(self.temp / "missing"),
             shared.FLAG_LIST_CHANGED),
            (shared.FLAG_PROJECT_ROOT, str(self.repo),
             shared.FLAG_LIST_CHANGED, shared.FLAG_BASE, "not-a-rev"),
        ]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"args={args}\n{result.stdout}{result.stderr}")


class CheckScopeTest(unittest.TestCase):
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
        # unconditionally excluded by the script, so the scope file itself
        # never counts as an untracked change.
        self.package = self.repo / ".tmp" / "t1" / "package"
        self.package.mkdir(parents=True)
        self.scope = self.package / "scope.md"

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), *args], capture_output=True, text=True, check=False
        )

    def default_args(self, scope: Path) -> tuple:
        return (
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_SCOPE_FILE, str(scope),
        )

    def test_pass_with_modified_and_new_files_declared(self) -> None:
        write_scope(self.scope, ("tracked.txt", "src/new.txt"))
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "new.txt").write_text("new\n", encoding="utf-8")

        result = self.run_script(*self.default_args(self.scope))

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn(shared.SCOPE_CHECK_PASS, result.stdout)
        self.assertIn("(2 changed, 2 declared)", result.stdout)

    def test_unicode_space_and_tab_path_is_matched_exactly(self) -> None:
        unusual = "中文 file\tname.txt"
        write_scope(self.scope, (unusual,))
        (self.repo / unusual).write_text("new\n", encoding="utf-8")

        result = self.run_script(*self.default_args(self.scope))

        self.assertEqual(
            result.returncode,
            shared.EXIT_PASS,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn(shared.SCOPE_CHECK_PASS, result.stdout)
        self.assertIn("(1 changed, 1 declared)", result.stdout)

    def test_out_of_scope_modified_file_fails(self) -> None:
        write_scope(self.scope, ("tracked.txt",))
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")
        (self.repo / "evil.txt").write_text("evil\n", encoding="utf-8")

        result = self.run_script(*self.default_args(self.scope))

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(f"{shared.OUT_OF_SCOPE} evil.txt", result.stdout)
        self.assertIn(shared.SCOPE_CHECK_FAIL, result.stdout)
        self.assertIn("(1 out-of-scope files)", result.stdout)

    def test_out_of_scope_modified_tracked_file_fails(self) -> None:
        write_scope(self.scope, ("src/ok.txt",))
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")

        result = self.run_script(*self.default_args(self.scope))

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(f"{shared.OUT_OF_SCOPE} tracked.txt", result.stdout)

    def test_tmp_paths_never_counted(self) -> None:
        write_scope(self.scope, ("tracked.txt",))
        tmp_junk = self.repo / ".tmp" / "x" / "junk.txt"
        tmp_junk.parent.mkdir(parents=True)
        tmp_junk.write_text("junk\n", encoding="utf-8")

        result = self.run_script(*self.default_args(self.scope))

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertNotIn(".tmp", result.stdout)

    def test_declared_but_unchanged_is_informational(self) -> None:
        write_scope(self.scope, ("tracked.txt", "unused.txt"))

        result = self.run_script(*self.default_args(self.scope))

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn(f"{shared.UNCHANGED} unused.txt", result.stdout)
        self.assertIn("(0 changed, 2 declared)", result.stdout)

    def test_infra_entries_counted_as_declared(self) -> None:
        write_scope(self.scope, ("tracked.txt",), infra=("pyproject.toml",))
        (self.repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

        result = self.run_script(*self.default_args(self.scope))

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn("(1 changed, 2 declared)", result.stdout)

    def test_staged_in_scope_passes_with_warning(self) -> None:
        write_scope(self.scope, ("tracked.txt",))
        (self.repo / "tracked.txt").write_text("staged\n", encoding="utf-8")
        git(self.repo, "add", "tracked.txt")

        result = self.run_script(*self.default_args(self.scope))

        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn(f"{shared.STAGED_WARNING} tracked.txt", result.stdout)

    def test_staged_out_of_scope_fails(self) -> None:
        write_scope(self.scope, ("tracked.txt",))
        (self.repo / "evil.txt").write_text("evil\n", encoding="utf-8")
        git(self.repo, "add", "evil.txt")

        result = self.run_script(*self.default_args(self.scope))

        self.assertEqual(result.returncode, shared.EXIT_FAIL)
        self.assertIn(f"{shared.OUT_OF_SCOPE} evil.txt", result.stdout)
        self.assertIn(f"{shared.STAGED_WARNING} evil.txt", result.stdout)

    def test_base_override_includes_later_commits(self) -> None:
        write_scope(self.scope, ("tracked.txt", "added-later.txt"))
        (self.repo / "added-later.txt").write_text("new\n", encoding="utf-8")
        git(self.repo, "add", "added-later.txt")
        git(self.repo, "commit", "-qm", "second")
        # Diff against the first commit includes the second commit's change.
        result = self.run_script(
            shared.FLAG_PROJECT_ROOT, str(self.repo),
            shared.FLAG_SCOPE_FILE, str(self.scope),
            shared.FLAG_BASE, self.base,
        )
        self.assertEqual(result.returncode, shared.EXIT_PASS)
        self.assertIn("(1 changed, 2 declared)", result.stdout)

    def test_usage_errors_exit_two(self) -> None:
        write_scope(self.scope, ("tracked.txt",))
        cases = [
            (),
            (shared.FLAG_PROJECT_ROOT,),
            (shared.FLAG_PROJECT_ROOT, str(self.repo)),
            (shared.FLAG_PROJECT_ROOT, str(self.temp / "missing"),
             shared.FLAG_SCOPE_FILE, str(self.scope)),
            (shared.FLAG_PROJECT_ROOT, str(self.temp / "missing"),
             shared.FLAG_SCOPE_FILE, str(self.scope),
             shared.FLAG_BASE, "HEAD"),
        ]
        # Non-git directory.
        non_git = self.temp / "non-git"
        non_git.mkdir()
        cases.append((shared.FLAG_PROJECT_ROOT, str(non_git),
                      shared.FLAG_SCOPE_FILE, str(self.scope)))
        # Missing scope file.
        cases.append((shared.FLAG_PROJECT_ROOT, str(self.repo),
                      shared.FLAG_SCOPE_FILE, str(self.repo / "nope.md")))
        # Scope file without files: section.
        empty_scope = self.repo / "empty-scope.md"
        empty_scope.write_text("## 范围声明\ntask: x\n", encoding="utf-8")
        cases.append((shared.FLAG_PROJECT_ROOT, str(self.repo),
                      shared.FLAG_SCOPE_FILE, str(empty_scope)))
        # Invalid base revision.
        cases.append((shared.FLAG_PROJECT_ROOT, str(self.repo),
                      shared.FLAG_SCOPE_FILE, str(self.scope),
                      shared.FLAG_BASE, "not-a-rev"))
        # Unknown argument.
        cases.append((shared.FLAG_PROJECT_ROOT, str(self.repo),
                      shared.FLAG_SCOPE_FILE, str(self.scope), "--bogus"))

        for args in cases:
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertEqual(result.returncode, shared.EXIT_USAGE,
                                 msg=f"args={args}\n{result.stdout}{result.stderr}")

    def test_unknown_argument_exits_two(self) -> None:
        write_scope(self.scope, ("tracked.txt",))
        result = self.run_script(*self.default_args(self.scope), "--bogus")
        self.assertEqual(result.returncode, shared.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
