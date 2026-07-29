from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


class DocumentationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.readme = README.read_text(encoding="utf-8")

    def assert_readme_contains(self, *snippets: str) -> None:
        for snippet in snippets:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.readme)

    def test_documents_platform_neutral_core_and_adapter_selection(self) -> None:
        self.assert_readme_contains(
            "Codex、Claude Code 与 Hermes",
            "平台无关",
            "runtime adapter",
            "只加载一个",
            "fail closed",
        )

    def test_documents_lifecycle_and_automatic_review(self) -> None:
        self.assert_readme_contains(
            "approved",
            "prepared",
            "dispatched",
            "authorized",
            "running",
            "handoff-received",
            "reviewing",
            "accepted",
            "committed",
            "finalized",
            "无需用户输入“继续”",
        )

    def test_documents_each_platform_runtime_contract(self) -> None:
        self.assert_readme_contains(
            "request_user_input",
            "spawn_agent",
            "two-phase",
            "wait_agent",
            "ExitPlanMode",
            "AskUserQuestion",
            "Agent(dev-with-tdd)",
            "atomic",
            "delegate_task",
            "clarify",
            "result reinjection",
            "可见性",
        )

    def test_documents_installation_and_platform_boundaries(self) -> None:
        self.assert_readme_contains(
            "https://github.com/douxc/agent-dev-workflow.git",
            "~/.agents/skills/plan-dev-tasks",
            "~/.agents/skills/dev-with-tdd",
            "~/.agents/platforms/claude-code/agents/",
            ".claude",
            ".claudeD",
            ".claudeP",
            ".codex/agents",
            ".hermes/agents",
            "新会话",
            "backup",
            "重复运行",
        )

    def test_documents_repository_layout_and_validation(self) -> None:
        self.assert_readme_contains(
            "adapters/claude-code/agents/",
            "runtime-adapters.md",
            "runtime-codex.md",
            "runtime-claude-code.md",
            "runtime-hermes.md",
            "python3 -m unittest discover -s tests -p 'test_*.py'",
            "python3 -m unittest discover -s skills/plan-dev-tasks/tests -p 'test_*.py'",
            "python3 -m unittest discover -s skills/dev-with-tdd/tests -p 'test_*.py'",
            "bash -n install.sh",
            "git diff --check",
        )


if __name__ == "__main__":
    unittest.main()
