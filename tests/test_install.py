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

    def test_replaces_canonical_and_platform_collisions_without_backups(
        self,
    ) -> None:
        canonical_root = self.home / ".agents" / "skills"
        canonical_root.mkdir(parents=True)
        historical_backups = []
        for skill in SKILLS:
            target = canonical_root / skill
            target.mkdir()
            (target / "old.txt").write_text(f"old {skill}", encoding="utf-8")
            historical_backup = canonical_root / f"{skill}.backup.historical"
            historical_backup.mkdir()
            (historical_backup / "keep.txt").write_text(
                f"historical {skill}", encoding="utf-8"
            )
            historical_backups.append(historical_backup)

        platform_root = self.home / ".claude"
        platform_skills = platform_root / "skills"
        platform_skills.mkdir(parents=True)
        file_collision = platform_skills / SKILLS[0]
        file_collision.write_text("user file", encoding="utf-8")
        dir_collision = platform_skills / SKILLS[1]
        dir_collision.mkdir()
        (dir_collision / "user.txt").write_text("user directory", encoding="utf-8")
        historical_platform_backup = (
            platform_skills / f"{SKILLS[0]}.backup.historical"
        )
        historical_platform_backup.write_text(
            "historical platform backup", encoding="utf-8"
        )

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_canonical_pair()
        for skill, historical_backup in zip(SKILLS, historical_backups):
            backups = list(canonical_root.glob(f"{skill}.backup.*"))
            self.assertEqual(backups, [historical_backup])
            self.assertEqual(
                (historical_backup / "keep.txt").read_text(encoding="utf-8"),
                f"historical {skill}",
            )

        file_backups = list(platform_skills.glob(f"{SKILLS[0]}.backup.*"))
        dir_backups = list(platform_skills.glob(f"{SKILLS[1]}.backup.*"))
        self.assertEqual(file_backups, [historical_platform_backup])
        self.assertEqual(
            historical_platform_backup.read_text(encoding="utf-8"),
            "historical platform backup",
        )
        self.assertEqual(dir_backups, [])

    def test_replaces_claude_agent_collisions_without_backups(self) -> None:
        canonical = (
            self.home / ".agents" / "platforms" / "claude-code" / "agents"
        )
        canonical.mkdir(parents=True)
        (canonical / "old.txt").write_text("old agents", encoding="utf-8")
        historical_canonical_backup = canonical.parent / "agents.backup.historical"
        historical_canonical_backup.mkdir()
        (historical_canonical_backup / "keep.txt").write_text(
            "historical agents", encoding="utf-8"
        )

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
        self.assertEqual(canonical_backups, [historical_canonical_backup])
        self.assertEqual(
            (historical_canonical_backup / "keep.txt").read_text(encoding="utf-8"),
            "historical agents",
        )
        for platform in CLAUDE_PLATFORMS:
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
            self.assertEqual(list(root.glob("agents.backup.*")), [])

    def test_recreates_correct_skill_links_on_reinstall(self) -> None:
        platform = self.home / ".codex"
        platform.mkdir()
        first = run_install(self.home)
        self.assert_success(first)
        links = [platform / "skills" / skill for skill in SKILLS]

        second = run_install(self.home)

        self.assert_success(second)
        self.assert_canonical_pair()
        for skill, link in zip(SKILLS, links):
            real_link = self.real_home / ".codex" / "skills" / skill
            self.assertTrue(link.is_symlink())
            self.assertEqual(
                os.readlink(link),
                str(self.real_home / ".agents" / "skills" / skill),
            )
            self.assertIn(
                f"remove {real_link}\nlink {real_link} ->",
                second.stdout,
            )
            self.assertNotIn(f"keep {real_link}", second.stdout)
            self.assertEqual(
                list(
                    (self.home / ".agents" / "skills").glob(
                        f"{skill}.backup.*"
                    )
                ),
                [],
            )

    def test_recreates_correct_claude_agents_link_while_refreshing_definitions(
        self,
    ) -> None:
        platform = self.home / ".claude"
        platform.mkdir()
        first = run_install(self.home)
        self.assert_success(first)
        link = platform / "agents"

        second = run_install(self.home)

        self.assert_success(second)
        self.assert_canonical_claude_agents()
        real_link = self.real_home / ".claude" / "agents"
        self.assertIn(
            f"remove {real_link}\nlink {real_link} ->",
            second.stdout,
        )
        self.assertNotIn(f"keep {real_link}", second.stdout)
        canonical = (
            self.home / ".agents" / "platforms" / "claude-code" / "agents"
        )
        self.assertEqual(list(canonical.parent.glob("agents.backup.*")), [])

    def test_rejects_invalid_platform_skills_before_replacing_targets(self) -> None:
        canonical = self.home / ".agents" / "skills" / SKILLS[0]
        canonical.mkdir(parents=True)
        marker = canonical / "old.txt"
        marker.write_text("keep until validation passes", encoding="utf-8")
        platform = self.home / ".claude"
        platform.mkdir()
        (platform / "skills").write_text("not a directory", encoding="utf-8")

        result = run_install(self.home)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("platform skills path is not a directory", result.stderr)
        self.assertEqual(
            marker.read_text(encoding="utf-8"),
            "keep until validation passes",
        )
        self.assertEqual(list(canonical.parent.glob(f"{SKILLS[0]}.backup.*")), [])

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
