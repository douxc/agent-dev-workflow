from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "install.sh"
SKILLS = shared.SKILL_NAMES
PLATFORMS = shared.PLATFORMS
LEGACY = shared.LEGACY_SKILLS


def run_install(
    home: str, script: Path = SCRIPT, args: tuple = ()
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = home
    return subprocess.run(
        [str(script), *args],
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

    def assert_skill_installed(self, platform: str, skill: str) -> None:
        installed = self.home / platform / "skills" / skill
        self.assertTrue(installed.is_dir(), msg=f"not a directory: {installed}")
        self.assertFalse(installed.is_symlink(), msg=f"is a symlink: {installed}")
        self.assertEqual(
            (installed / "SKILL.md").read_text(encoding="utf-8"),
            (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8"),
        )

    def assert_agent_installed(self, platform: str, agent: str) -> None:
        installed = self.home / platform / "agents" / f"{agent}.md"
        self.assertTrue(installed.is_file(), msg=f"not a file: {installed}")
        self.assertFalse(installed.is_symlink(), msg=f"is a symlink: {installed}")
        self.assertEqual(
            installed.read_text(encoding="utf-8"),
            (ROOT / "adapters" / "claude-code" / "agents" / f"{agent}.md")
            .read_text(encoding="utf-8"),
        )

    def assert_platforms_have_direct_copies(self) -> None:
        for platform in PLATFORMS:
            for skill in SKILLS:
                self.assert_skill_installed(platform, skill)
            for agent in SKILLS:
                self.assert_agent_installed(platform, agent)

    def test_script_is_executable(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_installs_direct_copies_into_existing_platforms(self) -> None:
        for platform in PLATFORMS:
            (self.home / platform).mkdir()

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_platforms_have_direct_copies()
        for platform in PLATFORMS:
            self.assertFalse((self.home / platform / "skills").is_symlink())

    def test_skips_missing_platform_roots_without_creating_them(self) -> None:
        result = run_install(self.home)

        self.assert_success(result)
        for platform in PLATFORMS:
            self.assertFalse((self.home / platform).exists())
            self.assertIn(f"skip {self.real_home / platform}", result.stdout)

    def test_replaces_skill_collisions_without_backups(self) -> None:
        platform_root = self.home / ".claude"
        platform_skills = platform_root / "skills"
        platform_skills.mkdir(parents=True)
        stale_skill = platform_skills / SKILLS[0]
        stale_skill.mkdir()
        (stale_skill / "SKILL.md").write_text("stale", encoding="utf-8")
        (stale_skill / "old.txt").write_text("old stale", encoding="utf-8")
        file_collision = platform_skills / SKILLS[1]
        file_collision.write_text("user file", encoding="utf-8")
        historical_backup = platform_skills / f"{SKILLS[0]}.backup.historical"
        historical_backup.write_text("historical backup", encoding="utf-8")

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_skill_installed(".claude", SKILLS[0])
        self.assert_skill_installed(".claude", SKILLS[1])
        self.assertFalse((stale_skill / "old.txt").exists())
        self.assertEqual(
            list(platform_skills.glob(f"{SKILLS[0]}.backup.*")),
            [historical_backup],
        )

    def test_agent_container_as_file_blocks_install_and_preserves_others(
        self,
    ) -> None:
        file_root = self.home / ".claudeP"
        file_root.mkdir()
        (file_root / "agents").write_text("user file", encoding="utf-8")
        dir_root = self.home / ".claudeD"
        (dir_root / "agents").mkdir(parents=True)
        stale_agent = dir_root / "agents" / f"{SKILLS[0]}.md"
        stale_agent.write_text("stale agent", encoding="utf-8")

        result = run_install(self.home)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("platform agents path is not a directory", result.stderr)
        self.assertEqual(
            stale_agent.read_text(encoding="utf-8"), "stale agent"
        )

    def test_replaces_symlink_based_install_with_direct_copies(self) -> None:
        platform_root = self.home / ".claude"
        platform_root.mkdir()
        legacy_canonical = self.home / "legacy-canonical"
        legacy_skills = legacy_canonical / "skills"
        legacy_skills.mkdir(parents=True)
        for skill in SKILLS:
            (legacy_skills / skill).mkdir()
            (legacy_skills / skill / "SKILL.md").write_text(
                f"stale {skill}", encoding="utf-8"
            )
            (platform_root / "skills").mkdir(exist_ok=True)
            (platform_root / "skills" / skill).symlink_to(legacy_skills / skill)
        legacy_agents = legacy_canonical / "agents"
        legacy_agents.mkdir(parents=True)
        (legacy_agents / f"{SKILLS[0]}.md").write_text(
            "stale agent", encoding="utf-8"
        )
        (platform_root / "agents").symlink_to(legacy_agents)

        result = run_install(self.home)

        self.assert_success(result)
        for skill in SKILLS:
            self.assert_skill_installed(".claude", skill)
        for agent in SKILLS:
            self.assert_agent_installed(".claude", agent)

    def test_recreates_correct_copies_on_reinstall(self) -> None:
        platform = self.home / ".claude"
        platform.mkdir()
        first = run_install(self.home)
        self.assert_success(first)

        second = run_install(self.home)

        self.assert_success(second)
        for skill in SKILLS:
            real_dest = self.real_home / ".claude" / "skills" / skill
            self.assertIn(
                f"remove {real_dest}\ninstall {real_dest}", second.stdout
            )
        for agent in SKILLS:
            real_dest = self.real_home / ".claude" / "agents" / f"{agent}.md"
            self.assertIn(
                f"remove {real_dest}\ninstall {real_dest}", second.stdout
            )

    def test_rejects_invalid_platform_skills_before_replacing_targets(
        self,
    ) -> None:
        preserved = self.home / ".claudeD" / "skills" / SKILLS[0]
        preserved.mkdir(parents=True)
        (preserved / "marker.txt").write_text(
            "keep until validation passes", encoding="utf-8"
        )
        platform = self.home / ".claude"
        platform.mkdir()
        (platform / "skills").write_text("not a directory", encoding="utf-8")

        result = run_install(self.home)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("platform skills path is not a directory", result.stderr)
        self.assertEqual(
            (preserved / "marker.txt").read_text(encoding="utf-8"),
            "keep until validation passes",
        )

    def test_removes_legacy_skills_and_agents(self) -> None:
        platform_root = self.home / ".claude"
        skills_dir = platform_root / "skills"
        agents_dir = platform_root / "agents"
        skills_dir.mkdir(parents=True)
        agents_dir.mkdir()
        legacy_skill = skills_dir / LEGACY[0]
        legacy_skill.mkdir()
        (legacy_skill / "SKILL.md").write_text("legacy", encoding="utf-8")
        legacy_agent = agents_dir / f"{LEGACY[0]}.md"
        legacy_agent.write_text("legacy agent", encoding="utf-8")
        unrelated = skills_dir / "unrelated-skill"
        unrelated.mkdir()
        (unrelated / "SKILL.md").write_text("keep me", encoding="utf-8")

        result = run_install(self.home)

        self.assert_success(result)
        self.assertFalse(legacy_skill.exists())
        self.assertFalse(legacy_agent.exists())
        self.assertIn(
            f"remove {self.real_home / '.claude' / 'skills' / LEGACY[0]}",
            result.stdout,
        )
        # Unrelated skill dirs are untouched.
        self.assertEqual(
            (unrelated / "SKILL.md").read_text(encoding="utf-8"), "keep me"
        )

    def test_removes_legacy_across_all_platforms(self) -> None:
        for platform in PLATFORMS:
            skills_dir = self.home / platform / "skills"
            agents_dir = self.home / platform / "agents"
            skills_dir.mkdir(parents=True)
            agents_dir.mkdir()
            for legacy in LEGACY:
                legacy_dir = skills_dir / legacy
                legacy_dir.mkdir()
                (legacy_dir / "SKILL.md").write_text("legacy", encoding="utf-8")
                (agents_dir / f"{legacy}.md").write_text(
                    "legacy agent", encoding="utf-8"
                )

        result = run_install(self.home)

        self.assert_success(result)
        for platform in PLATFORMS:
            for legacy in LEGACY:
                self.assertFalse(
                    (self.home / platform / "skills" / legacy).exists()
                )
                self.assertFalse(
                    (self.home / platform / "agents" / f"{legacy}.md").exists()
                )

    def test_rejects_empty_root_or_missing_home(self) -> None:
        for home in ("", "/", str(self.temp / "missing-home")):
            with self.subTest(home=home):
                result = run_install(home)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("HOME", result.stderr)

    def test_rejects_unknown_arguments(self) -> None:
        result = subprocess.run(
            [str(SCRIPT), "--bogus"],
            cwd=SCRIPT.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown argument", result.stderr)

    def test_rejects_missing_skill_sources_before_installing(self) -> None:
        fake_repo = self.temp / "incomplete-repo"
        fake_repo.mkdir()
        fake_script = fake_repo / "install.sh"
        shutil.copy2(SCRIPT, fake_script)
        fake_script.chmod(0o755)
        fake_skills = fake_repo / "skills"
        fake_skills.mkdir()
        shutil.copytree(ROOT / "skills" / SKILLS[0], fake_skills / SKILLS[0])
        incomplete_home = self.temp / "incomplete-home"
        incomplete_home.mkdir()
        (incomplete_home / ".claude").mkdir()

        result = run_install(incomplete_home, fake_script)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source skill", result.stderr)
        for skill in SKILLS:
            self.assertFalse(
                (incomplete_home / ".claude" / "skills" / skill).exists()
            )

    def hermes_profile_root(self, profile: str = "coder") -> Path:
        return self.home / ".hermes" / "profiles" / profile

    def assert_hermes_skill_installed(self, profile: str, skill: str) -> None:
        installed = self.hermes_profile_root(profile) / "skills" / skill
        self.assertTrue(installed.is_dir(), msg=f"not a directory: {installed}")
        self.assertFalse(installed.is_symlink(), msg=f"is a symlink: {installed}")
        self.assertEqual(
            (installed / "SKILL.md").read_text(encoding="utf-8"),
            (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8"),
        )

    def test_installs_skills_into_named_hermes_profile(self) -> None:
        profile_root = self.hermes_profile_root()
        (profile_root / "skills").mkdir(parents=True)

        result = run_install(self.home, args=("-p", "coder"))

        self.assert_success(result)
        for skill in SKILLS:
            self.assert_hermes_skill_installed("coder", skill)
            real_dest = (
                self.real_home / ".hermes" / "profiles" / "coder"
                / "skills" / skill
            )
            self.assertIn(f"install {real_dest}", result.stdout)

    def test_hermes_mode_ships_no_agents_and_touches_no_claude_platforms(
        self,
    ) -> None:
        profile_root = self.hermes_profile_root()
        (profile_root / "skills").mkdir(parents=True)

        result = run_install(self.home, args=("-p", "coder"))

        self.assert_success(result)
        self.assertFalse((profile_root / "agents").exists())
        self.assertNotIn("/agents/", result.stdout)
        for platform in PLATFORMS:
            self.assertFalse((self.home / platform).exists())

    def test_plain_mode_never_creates_hermes_paths(self) -> None:
        for platform in PLATFORMS:
            (self.home / platform).mkdir()

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_platforms_have_direct_copies()
        self.assertFalse((self.home / ".hermes").exists())

    def test_hermes_mode_skips_missing_profile_without_creating_it(self) -> None:
        result = run_install(self.home, args=("-p", "missing"))

        self.assert_success(result)
        self.assertFalse(self.hermes_profile_root("missing").exists())
        self.assertIn(
            f"skip {self.real_home / '.hermes' / 'profiles' / 'missing'}",
            result.stdout,
        )

    def test_hermes_mode_rejects_bad_inputs_and_blocking_paths(self) -> None:
        cases = (
            (("-p",), "-p requires"),
            (("-p", "a/b"), "invalid profile name"),
            (("--bogus",), "unknown argument"),
        )
        for args, err in cases:
            with self.subTest(args=args):
                result = subprocess.run(
                    [str(SCRIPT), *args],
                    cwd=SCRIPT.parent,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(err, result.stderr)

        profile_root = self.hermes_profile_root()
        profile_root.mkdir(parents=True)
        (profile_root / "skills").write_text("user file", encoding="utf-8")
        result = run_install(self.home, args=("-p", "coder"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("platform skills path is not a directory", result.stderr)

    def test_hermes_mode_removes_legacy_skills_from_profile(self) -> None:
        skills_dir = self.hermes_profile_root() / "skills"
        skills_dir.mkdir(parents=True)
        legacy_dir = skills_dir / LEGACY[0]
        legacy_dir.mkdir()
        (legacy_dir / "SKILL.md").write_text("legacy", encoding="utf-8")

        result = run_install(self.home, args=("-p", "coder"))

        self.assert_success(result)
        self.assertFalse(legacy_dir.exists())
        for skill in SKILLS:
            self.assert_hermes_skill_installed("coder", skill)

    def test_rejects_missing_agent_sources_before_installing(self) -> None:
        fake_repo = self.temp / "missing-agent-repo"
        fake_repo.mkdir()
        fake_script = fake_repo / "install.sh"
        shutil.copy2(SCRIPT, fake_script)
        fake_script.chmod(0o755)
        shutil.copytree(ROOT / "skills", fake_repo / "skills")
        incomplete_home = self.temp / "missing-agent-home"
        incomplete_home.mkdir()
        (incomplete_home / ".claude").mkdir()

        result = run_install(incomplete_home, fake_script)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source Claude Code agent", result.stderr)
        for skill in SKILLS:
            self.assertFalse(
                (incomplete_home / ".claude" / "skills" / skill).exists()
            )


if __name__ == "__main__":
    unittest.main()
