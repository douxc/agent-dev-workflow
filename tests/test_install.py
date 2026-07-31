from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
from typing import Sequence, Union
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "install.sh"
SKILLS = ("plan-dev-tasks", "dev-with-tdd")
PLATFORMS = (".claude", ".claudeD", ".claudeP", ".hermes")
CLAUDE_PLATFORMS = (".claude", ".claudeD", ".claudeP")
CLAUDE_AGENT_NAMES = ("plan-dev-tasks", "dev-with-tdd")


def run_install(
    home: Union[Path, str],
    script: Path = SCRIPT,
    args: Sequence[str] = (),
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(home)
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

    def hermes_profile(self, name: str) -> Path:
        return self.home / ".hermes" / "profiles" / name

    def assert_skill_installed(
        self, rel: Union[str, Path], skill: str
    ) -> None:
        installed = self.home / rel / "skills" / skill
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
            (
                ROOT
                / "adapters"
                / "claude-code"
                / "agents"
                / f"{agent}.md"
            ).read_text(encoding="utf-8"),
        )

    def assert_platforms_have_direct_copies(self) -> None:
        for platform in PLATFORMS:
            for skill in SKILLS:
                self.assert_skill_installed(platform, skill)
        for platform in CLAUDE_PLATFORMS:
            for agent in CLAUDE_AGENT_NAMES:
                self.assert_agent_installed(platform, agent)
        self.assertFalse((self.home / ".hermes" / "agents").exists())

    def test_script_is_executable(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_installs_direct_copies_into_existing_platforms(self) -> None:
        for platform in PLATFORMS:
            (self.home / platform).mkdir()

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_platforms_have_direct_copies()
        # No symlink indirection: skills live directly where each platform discovers them.
        for platform in PLATFORMS:
            skills_dir = self.home / platform / "skills"
            self.assertFalse(skills_dir.is_symlink())

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

        # A stale real copy from a previous direct-copy install.
        stale_skill = platform_skills / SKILLS[0]
        stale_skill.mkdir()
        (stale_skill / "SKILL.md").write_text("stale", encoding="utf-8")
        (stale_skill / "old.txt").write_text("old stale", encoding="utf-8")

        # A stray file occupying a skill slot.
        file_collision = platform_skills / SKILLS[1]
        file_collision.write_text("user file", encoding="utf-8")

        # An adjacent historical backup the installer must never touch or scan.
        historical_backup = platform_skills / f"{SKILLS[0]}.backup.historical"
        historical_backup.write_text("historical backup", encoding="utf-8")

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_skill_installed(".claude", SKILLS[0])
        self.assert_skill_installed(".claude", SKILLS[1])
        self.assertFalse((stale_skill / "old.txt").exists())
        backups = list(platform_skills.glob(f"{SKILLS[0]}.backup.*"))
        self.assertEqual(backups, [historical_backup])
        self.assertEqual(
            historical_backup.read_text(encoding="utf-8"),
            "historical backup",
        )

    def test_agent_container_as_file_blocks_install_and_preserves_others(self) -> None:
        # A stray file at .claudeP/agents must block before any agent is replaced.
        file_root = self.home / ".claudeP"
        file_root.mkdir()
        (file_root / "agents").write_text("user file", encoding="utf-8")

        # A real agent dir in .claudeD must survive the failed run untouched.
        dir_root = self.home / ".claudeD"
        (dir_root / "agents").mkdir(parents=True)
        (dir_root / "agents" / f"{CLAUDE_AGENT_NAMES[0]}.md").write_text(
            "stale agent", encoding="utf-8"
        )

        result = run_install(self.home)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("platform agents path is not a directory", result.stderr)
        self.assertEqual(
            (dir_root / "agents" / f"{CLAUDE_AGENT_NAMES[0]}.md").read_text(
                encoding="utf-8"
            ),
            "stale agent",
        )

    def test_replaces_stale_agent_files_and_preserves_historical_backups(self) -> None:
        # A real agents/ dir with a stale agent file and an adjacent historical backup.
        platform_root = self.home / ".claude"
        (platform_root / "agents").mkdir(parents=True)
        (platform_root / "agents" / f"{CLAUDE_AGENT_NAMES[0]}.md").write_text(
            "stale agent", encoding="utf-8"
        )
        historical_backup = (
            platform_root / "agents" / f"{CLAUDE_AGENT_NAMES[0]}.backup.historical"
        )
        historical_backup.write_text("historical agent backup", encoding="utf-8")

        result = run_install(self.home)

        self.assert_success(result)
        self.assert_agent_installed(".claude", CLAUDE_AGENT_NAMES[0])
        self.assert_agent_installed(".claude", CLAUDE_AGENT_NAMES[1])
        self.assertEqual(
            list((platform_root / "agents").glob(f"{CLAUDE_AGENT_NAMES[0]}.backup.*")),
            [historical_backup],
        )
        self.assertEqual(
            historical_backup.read_text(encoding="utf-8"),
            "historical agent backup",
        )

    def test_replaces_symlink_based_install_with_direct_copies(self) -> None:
        platform_root = self.home / ".claude"
        platform_root.mkdir()

        # Simulate a pre-existing symlink-based install: skill slots and agents/
        # are symlinks pointing at an external canonical source.
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
        (legacy_agents / f"{CLAUDE_AGENT_NAMES[0]}.md").write_text(
            "stale agent", encoding="utf-8"
        )
        (platform_root / "agents").symlink_to(legacy_agents)

        result = run_install(self.home)

        self.assert_success(result)
        # Symlinks are gone; real copies with fresh source content are in place.
        for skill in SKILLS:
            self.assert_skill_installed(".claude", skill)
        for agent in CLAUDE_AGENT_NAMES:
            self.assert_agent_installed(".claude", agent)

    def test_recreates_correct_skill_copies_on_reinstall(self) -> None:
        platform = self.home / ".hermes"
        platform.mkdir()
        first = run_install(self.home)
        self.assert_success(first)
        dests = [platform / "skills" / skill for skill in SKILLS]

        second = run_install(self.home)

        self.assert_success(second)
        for skill, dest in zip(SKILLS, dests):
            real_dest = self.real_home / ".hermes" / "skills" / skill
            self.assertIn(
                f"remove {real_dest}\ninstall {real_dest}",
                second.stdout,
            )
            self.assertNotIn(f"keep {real_dest}", second.stdout)
            self.assertEqual(
                list((platform / "skills").glob(f"{skill}.backup.*")),
                [],
            )
        self.assert_skill_installed(".hermes", SKILLS[0])

    def test_recreates_correct_claude_agents_on_reinstall(self) -> None:
        platform = self.home / ".claude"
        platform.mkdir()
        first = run_install(self.home)
        self.assert_success(first)
        agent = CLAUDE_AGENT_NAMES[0]
        dest = platform / "agents" / f"{agent}.md"

        second = run_install(self.home)

        self.assert_success(second)
        real_dest = self.real_home / ".claude" / "agents" / f"{agent}.md"
        self.assertIn(
            f"remove {real_dest}\ninstall {real_dest}",
            second.stdout,
        )
        self.assertNotIn(f"keep {real_dest}", second.stdout)
        self.assertEqual(list((platform / "agents").glob(f"{agent}.backup.*")), [])
        self.assert_agent_installed(".claude", agent)

    def test_rejects_invalid_platform_skills_before_replacing_targets(self) -> None:
        # A pre-existing real copy in .hermes must survive when .claude is invalid.
        preserved = self.home / ".hermes" / "skills" / SKILLS[0]
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
        self.assertEqual(list((self.home / ".hermes" / "skills").glob("*.backup.*")), [])

    def test_hermes_never_receives_agent_directory(self) -> None:
        (self.home / ".hermes").mkdir()

        result = run_install(self.home)

        self.assert_success(result)
        self.assertFalse((self.home / ".hermes" / "agents").exists())

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
        (incomplete_home / ".claude").mkdir()

        result = run_install(incomplete_home, fake_script)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source skill", result.stderr)
        # Validation runs before any mutation: nothing is installed anywhere.
        for skill in SKILLS:
            self.assertFalse(
                (incomplete_home / ".claude" / "skills" / skill).exists()
            )

    def test_rejects_missing_claude_agent_sources_before_installing(self) -> None:
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

    def test_installs_into_named_hermes_profile(self) -> None:
        profile = self.hermes_profile("dev")
        profile.mkdir(parents=True)

        result = run_install(self.home, args=("--hermes-profile", "dev"))

        self.assert_success(result)
        for skill in SKILLS:
            self.assert_skill_installed(
                Path(".hermes") / "profiles" / "dev", skill
            )
        # Named profiles never receive agents/, same as the .hermes platform.
        self.assertFalse((profile / "agents").exists())

    def test_skips_missing_hermes_profile_without_creating_it(self) -> None:
        result = run_install(self.home, args=("--hermes-profile", "dev"))

        self.assert_success(result)
        self.assertIn(
            (
                f"skip {self.real_home}/.hermes/profiles/dev "
                "(profile root missing)"
            ),
            result.stdout,
        )
        self.assertFalse((self.home / ".hermes").exists())

    def test_installs_into_multiple_hermes_profiles(self) -> None:
        dev = self.hermes_profile("dev")
        qa = self.hermes_profile("qa")
        dev.mkdir(parents=True)
        qa.mkdir(parents=True)
        # dev/qa creation above already bootstrapped the .hermes default root.
        (self.home / ".hermes").mkdir(exist_ok=True)

        result = run_install(
            self.home,
            args=("--hermes-profile", "dev", "--hermes-profile", "qa"),
        )

        self.assert_success(result)
        for skill in SKILLS:
            self.assert_skill_installed(
                Path(".hermes") / "profiles" / "dev", skill
            )
            self.assert_skill_installed(
                Path(".hermes") / "profiles" / "qa", skill
            )
        # Additive: the default .hermes platform root is still installed.
        self.assert_skill_installed(".hermes", SKILLS[0])
        for profile in (dev, qa):
            self.assertFalse((profile / "agents").exists())
        self.assertFalse((self.home / ".hermes" / "agents").exists())

    def test_recreates_profile_skills_on_reinstall(self) -> None:
        profile = self.hermes_profile("dev")
        profile.mkdir(parents=True)
        args = ("--hermes-profile", "dev")

        first = run_install(self.home, args=args)
        self.assert_success(first)
        second = run_install(self.home, args=args)

        self.assert_success(second)
        for skill in SKILLS:
            real_dest = (
                self.real_home
                / ".hermes"
                / "profiles"
                / "dev"
                / "skills"
                / skill
            )
            self.assertIn(
                f"remove {real_dest}\ninstall {real_dest}",
                second.stdout,
            )
            self.assertNotIn(f"keep {real_dest}", second.stdout)
            self.assertEqual(
                list((profile / "skills").glob(f"{skill}.backup.*")),
                [],
            )
        self.assert_skill_installed(
            Path(".hermes") / "profiles" / "dev", SKILLS[0]
        )

    def test_rejects_invalid_hermes_profile_names_before_mutation(self) -> None:
        # A pre-existing real copy in .claude must survive every rejected name.
        preserved = self.home / ".claude" / "skills" / SKILLS[0]
        preserved.mkdir(parents=True)
        (preserved / "marker.txt").write_text(
            "keep until validation passes", encoding="utf-8"
        )

        invalid_names = (
            ".",
            "..",
            "../evil",
            "/tmp/abs",
            "a/b",
            "has space",
            "a\tb",
            ".hidden",
            "-dash",
            "~tilde",
        )
        for name in invalid_names:
            with self.subTest(name=name):
                result = run_install(
                    self.home, args=("--hermes-profile", name)
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("invalid Hermes profile name", result.stderr)
                self.assertEqual(
                    (preserved / "marker.txt").read_text(encoding="utf-8"),
                    "keep until validation passes",
                )

    def test_rejects_hermes_profile_flag_without_argument(self) -> None:
        for args in (("--hermes-profile",), ("--hermes-profile", "")):
            with self.subTest(args=args):
                result = run_install(self.home, args=args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "--hermes-profile requires a non-empty profile name",
                    result.stderr,
                )

    def test_rejects_unknown_arguments(self) -> None:
        result = run_install(self.home, args=("--bogus",))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown argument: --bogus", result.stderr)

    def test_rejects_blocking_file_at_profile_skills_before_mutating_others(
        self,
    ) -> None:
        # A pre-existing real copy in .hermes must survive when a named
        # profile's skills path is a blocking file.
        preserved = self.home / ".hermes" / "skills" / SKILLS[0]
        preserved.mkdir(parents=True)
        (preserved / "marker.txt").write_text(
            "keep until validation passes", encoding="utf-8"
        )

        profile = self.hermes_profile("dev")
        profile.mkdir(parents=True)
        (profile / "skills").write_text("not a directory", encoding="utf-8")

        result = run_install(self.home, args=("--hermes-profile", "dev"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("profile skills path is not a directory", result.stderr)
        self.assertEqual(
            (preserved / "marker.txt").read_text(encoding="utf-8"),
            "keep until validation passes",
        )
        self.assertEqual(
            list((self.home / ".hermes" / "skills").glob("*.backup.*")),
            [],
        )

    def test_hermes_profiles_untouched_without_flag(self) -> None:
        stale = (
            self.hermes_profile("dev") / "skills" / SKILLS[0] / "SKILL.md"
        )
        stale.parent.mkdir(parents=True)
        stale.write_text("stale profile copy", encoding="utf-8")

        result = run_install(self.home)

        self.assert_success(result)
        self.assertEqual(
            stale.read_text(encoding="utf-8"), "stale profile copy"
        )
        self.assertNotIn(".hermes/profiles", result.stdout)

    def load_settings(self, platform: str) -> dict:
        import json

        return json.loads(
            (self.home / platform / "settings.json").read_text(encoding="utf-8")
        )

    def test_harden_merges_hooks_into_existing_settings(self) -> None:
        (self.home / ".claude").mkdir()
        settings = self.home / ".claude" / "settings.json"
        settings.write_text(
            '{"permissions": {"allow": ["Bash(git log)"]}}', encoding="utf-8"
        )

        result = run_install(self.home, args=("--harden-claude",))

        self.assert_success(result)
        data = self.load_settings(".claude")
        self.assertEqual(
            data["permissions"], {"allow": ["Bash(git log)"]}
        )
        pretool = data["hooks"]["PreToolUse"]
        self.assertEqual(
            {group["matcher"] for group in pretool},
            {"Write", "Edit", "MultiEdit", "Bash", "Agent"},
        )
        self.assertTrue(data["hooks"]["Stop"])
        # Hook commands point at the installed bundle.
        command = pretool[0]["hooks"][0]["command"]
        self.assertIn("/.claude/skills/plan-dev-tasks/scripts/hooks/", command)

    def test_harden_creates_settings_when_absent(self) -> None:
        (self.home / ".claude").mkdir()

        result = run_install(self.home, args=("--harden-claude",))

        self.assert_success(result)
        data = self.load_settings(".claude")
        self.assertEqual(
            len(data["hooks"]["PreToolUse"]), 5
        )

    def test_harden_rejects_invalid_settings_and_leaves_untouched(self) -> None:
        (self.home / ".claude").mkdir()
        settings = self.home / ".claude" / "settings.json"
        settings.write_text("{not json", encoding="utf-8")

        result = run_install(self.home, args=("--harden-claude",))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("harden step failed", result.stderr)
        self.assertEqual(
            settings.read_text(encoding="utf-8"), "{not json"
        )

    def test_harden_is_idempotent(self) -> None:
        (self.home / ".claude").mkdir()
        args = ("--harden-claude",)

        self.assert_success(run_install(self.home, args=args))
        second = run_install(self.home, args=args)

        self.assert_success(second)
        data = self.load_settings(".claude")
        self.assertEqual(len(data["hooks"]["PreToolUse"]), 5)

    def test_unharden_removes_only_bundle_entries(self) -> None:
        (self.home / ".claude").mkdir()
        self.assert_success(
            run_install(self.home, args=("--harden-claude",))
        )
        data = self.load_settings(".claude")
        data["hooks"]["PreToolUse"][0]["hooks"].append(
            {"type": "command", "command": "python3 /foreign/hook.py"}
        )
        (self.home / ".claude" / "settings.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        result = run_install(self.home, args=("--unharden-claude",))

        self.assert_success(result)
        data = self.load_settings(".claude")
        # Foreign entries survive; bundle entries are gone.
        self.assertIn("python3 /foreign/hook.py", str(data))
        self.assertNotIn("plan-dev-tasks/scripts/hooks", str(data))

    def test_harden_requires_claude_platform_root(self) -> None:
        (self.home / ".hermes").mkdir()

        result = run_install(self.home, args=("--harden-claude",))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--harden-claude requires at least one existing Claude Code platform root",
            result.stderr,
        )

    def test_harden_flags_are_mutually_exclusive(self) -> None:
        (self.home / ".claude").mkdir()

        result = run_install(
            self.home,
            args=("--harden-claude", "--unharden-claude"),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mutually exclusive", result.stderr)

    def test_harden_never_touches_hermes(self) -> None:
        (self.home / ".claude").mkdir()
        (self.home / ".hermes").mkdir()

        result = run_install(self.home, args=("--harden-claude",))

        self.assert_success(result)
        self.assertFalse((self.home / ".hermes" / "settings.json").exists())


if __name__ == "__main__":
    unittest.main()
