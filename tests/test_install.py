from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from typing import Union
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "install.sh"
SKILLS = ("plan-dev-tasks", "dev-with-tdd")
PLATFORMS = (".claude", ".claudeD", ".claudeP", ".codex", ".hermes")
CLAUDE_PLATFORMS = (".claude", ".claudeD", ".claudeP")
CLAUDE_AGENT_NAMES = ("plan-dev-tasks", "dev-with-tdd")


def run_install(
    home: Union[Path, str], script: Path = SCRIPT
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        [str(script)],
        cwd=script.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class InstallScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp = Path(self.temp_dir.name)
        self.home = self.temp / "home"
        self.home.mkdir()
        self.real_home = self.home.resolve()

    def assert_success(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def assert_canonical_pair(self) -> None:
        for skill in SKILLS:
            installed = self.home / ".agents" / "skills" / skill
            self.assertTrue(installed.is_dir())
            self.assertFalse(installed.is_symlink())
            self.assertEqual(
                (installed / "SKILL.md").read_text(encoding="utf-8"),
                (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8"),
            )

    def assert_canonical_claude_agents(self) -> None:
        canonical = (
            self.home / ".agents" / "platforms" / "claude-code" / "agents"
        )
        self.assertTrue(canonical.is_dir())
        self.assertFalse(canonical.is_symlink())
        for agent in CLAUDE_AGENT_NAMES:
            self.assertEqual(
                (canonical / f"{agent}.md").read_text(encoding="utf-8"),
                (
                    ROOT
                    / "adapters"
                    / "claude-code"
                    / "agents"
                    / f"{agent}.md"
                ).read_text(encoding="utf-8"),
            )

    def test_script_is_executable(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_installs_canonical_pair_and_links_existing_platforms(self) -> None:
        for platform in PLATFORMS:
            (self.home / platform).mkdir()

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_canonical_pair()
        self.assert_canonical_claude_agents()
        for platform in PLATFORMS:
            for skill in SKILLS:
                link = self.home / platform / "skills" / skill
                target = self.real_home / ".agents" / "skills" / skill
                self.assertTrue(link.is_symlink())
                self.assertEqual(os.readlink(link), str(target))
                self.assertTrue(os.path.isabs(os.readlink(link)))
        for platform in CLAUDE_PLATFORMS:
            link = self.home / platform / "agents"
            target = (
                self.real_home
                / ".agents"
                / "platforms"
                / "claude-code"
                / "agents"
            )
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), str(target))
            self.assertTrue(os.path.isabs(os.readlink(link)))
        for platform in (".codex", ".hermes"):
            self.assertFalse((self.home / platform / "agents").exists())

    def test_skips_missing_platform_roots_without_creating_them(self) -> None:
        result = run_install(self.home)

        self.assert_success(result)
        self.assert_canonical_pair()
        self.assert_canonical_claude_agents()
        for platform in PLATFORMS:
            self.assertFalse((self.home / platform).exists())
            self.assertIn(f"skip {self.real_home / platform}", result.stdout)

    def test_backs_up_canonical_and_platform_collisions(self) -> None:
        canonical_root = self.home / ".agents" / "skills"
        canonical_root.mkdir(parents=True)
        for skill in SKILLS:
            target = canonical_root / skill
            target.mkdir()
            (target / "old.txt").write_text(f"old {skill}", encoding="utf-8")

        platform_root = self.home / ".claude"
        platform_skills = platform_root / "skills"
        platform_skills.mkdir(parents=True)
        file_collision = platform_skills / SKILLS[0]
        file_collision.write_text("user file", encoding="utf-8")
        dir_collision = platform_skills / SKILLS[1]
        dir_collision.mkdir()
        (dir_collision / "user.txt").write_text("user directory", encoding="utf-8")

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_canonical_pair()
        for skill in SKILLS:
            backups = list(canonical_root.glob(f"{skill}.backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(
                (backups[0] / "old.txt").read_text(encoding="utf-8"),
                f"old {skill}",
            )

        file_backups = list(platform_skills.glob(f"{SKILLS[0]}.backup.*"))
        dir_backups = list(platform_skills.glob(f"{SKILLS[1]}.backup.*"))
        self.assertEqual(len(file_backups), 1)
        self.assertEqual(file_backups[0].read_text(encoding="utf-8"), "user file")
        self.assertEqual(len(dir_backups), 1)
        self.assertEqual(
            (dir_backups[0] / "user.txt").read_text(encoding="utf-8"),
            "user directory",
        )

    def test_backs_up_claude_agent_canonical_and_link_collisions(self) -> None:
        canonical = (
            self.home / ".agents" / "platforms" / "claude-code" / "agents"
        )
        canonical.mkdir(parents=True)
        (canonical / "old.txt").write_text("old agents", encoding="utf-8")

        file_root = self.home / ".claude"
        file_root.mkdir()
        (file_root / "agents").write_text("user file", encoding="utf-8")

        dir_root = self.home / ".claudeD"
        (dir_root / "agents").mkdir(parents=True)
        (dir_root / "agents" / "user.txt").write_text(
            "user directory", encoding="utf-8"
        )

        wrong_link_root = self.home / ".claudeP"
        wrong_link_root.mkdir()
        (wrong_link_root / "agents").symlink_to(self.home / "wrong-agents")

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_canonical_claude_agents()
        canonical_backups = list(canonical.parent.glob("agents.backup.*"))
        self.assertEqual(len(canonical_backups), 1)
        self.assertEqual(
            (canonical_backups[0] / "old.txt").read_text(encoding="utf-8"),
            "old agents",
        )
        for platform, old_value in (
            (".claude", "user file"),
            (".claudeD", "user directory"),
            (".claudeP", str(self.home / "wrong-agents")),
        ):
            root = self.home / platform
            link = root / "agents"
            self.assertTrue(link.is_symlink())
            self.assertEqual(
                os.readlink(link),
                str(
                    self.real_home
                    / ".agents"
                    / "platforms"
                    / "claude-code"
                    / "agents"
                ),
            )
            backups = list(root.glob("agents.backup.*"))
            self.assertEqual(len(backups), 1)
            if platform == ".claude":
                self.assertEqual(backups[0].read_text(encoding="utf-8"), old_value)
            elif platform == ".claudeD":
                self.assertEqual(
                    (backups[0] / "user.txt").read_text(encoding="utf-8"),
                    old_value,
                )
            else:
                self.assertTrue(backups[0].is_symlink())
                self.assertEqual(os.readlink(backups[0]), old_value)

    def test_keeps_correct_links_while_reinstalling_canonical_pair(self) -> None:
        platform = self.home / ".codex"
        platform.mkdir()
        first = run_install(self.home)
        self.assert_success(first)
        links = [platform / "skills" / skill for skill in SKILLS]
        first_inodes = [link.lstat().st_ino for link in links]

        second = run_install(self.home)

        self.assert_success(second)
        self.assert_canonical_pair()
        self.assertEqual([link.lstat().st_ino for link in links], first_inodes)
        for skill, link in zip(SKILLS, links):
            real_link = self.real_home / ".codex" / "skills" / skill
            self.assertIn(f"keep {real_link}", second.stdout)
            backups = list(
                (self.home / ".agents" / "skills").glob(f"{skill}.backup.*")
            )
            self.assertEqual(len(backups), 1)

    def test_keeps_correct_claude_agents_link_while_refreshing_definitions(
        self,
    ) -> None:
        platform = self.home / ".claude"
        platform.mkdir()
        first = run_install(self.home)
        self.assert_success(first)
        link = platform / "agents"
        first_inode = link.lstat().st_ino

        second = run_install(self.home)

        self.assert_success(second)
        self.assert_canonical_claude_agents()
        self.assertEqual(link.lstat().st_ino, first_inode)
        self.assertIn(
            f"keep {self.real_home / '.claude' / 'agents'}",
            second.stdout,
        )
        canonical = (
            self.home / ".agents" / "platforms" / "claude-code" / "agents"
        )
        self.assertEqual(len(list(canonical.parent.glob("agents.backup.*"))), 1)

    def test_codex_and_hermes_never_receive_agent_directories(self) -> None:
        for platform in (".codex", ".hermes"):
            (self.home / platform).mkdir()

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_canonical_claude_agents()
        for platform in (".codex", ".hermes"):
            self.assertFalse((self.home / platform / "agents").exists())

    def test_rejects_empty_root_or_missing_home(self) -> None:
        for home in ("", "/", self.temp / "missing-home"):
            with self.subTest(home=home):
                result = run_install(home)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("HOME", result.stderr)

    def test_rejects_missing_skill_sources_before_installing(self) -> None:
        fake_repo = self.temp / "incomplete-repo"
        fake_repo.mkdir()
        fake_script = fake_repo / "install.sh"
        shutil.copy2(SCRIPT, fake_script)
        fake_script.chmod(0o755)
        fake_skills = fake_repo / "skills"
        fake_skills.mkdir()
        shutil.copytree(
            ROOT / "skills" / SKILLS[0],
            fake_skills / SKILLS[0],
        )
        incomplete_home = self.temp / "incomplete-home"
        incomplete_home.mkdir()

        result = run_install(incomplete_home, fake_script)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source skill", result.stderr)
        self.assertFalse((incomplete_home / ".agents").exists())

    def test_rejects_missing_claude_agent_sources_before_installing(self) -> None:
        fake_repo = self.temp / "missing-agent-repo"
        fake_repo.mkdir()
        fake_script = fake_repo / "install.sh"
        shutil.copy2(SCRIPT, fake_script)
        fake_script.chmod(0o755)
        shutil.copytree(ROOT / "skills", fake_repo / "skills")
        incomplete_home = self.temp / "missing-agent-home"
        incomplete_home.mkdir()

        result = run_install(incomplete_home, fake_script)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source Claude Code agent", result.stderr)
        self.assertFalse((incomplete_home / ".agents").exists())


if __name__ == "__main__":
    unittest.main()
