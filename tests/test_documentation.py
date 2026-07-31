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

    def test_documents_platform_neutral_core_and_flow_selection(self) -> None:
        self.assert_readme_contains(
            "Claude Code 与 Hermes",
            "平台无关",
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
            "直接复制到每个已存在平台根目录的 `skills/` 下",
            "~/.claude/skills/plan-dev-tasks",
            "~/.claude/skills/dev-with-tdd",
            "直接复制到每个已存在的 `.claude`、`.claudeD`、`.claudeP` 的 `agents/` 下",
            "~/.claude/agents/plan-dev-tasks.md",
            "~/.claude/agents/dev-with-tdd.md",
            "源仓库是唯一 canonical 来源",
            "不保留单独的 canonical 副本",
            "也不创建任何软链接",
            ".claude",
            ".claudeD",
            ".claudeP",
            "--hermes-profile <name>",
            ".hermes/agents",
            "新会话",
            "永久删除",
            "先删除再",
            "不会创建新的 `.backup.*`",
            "不会扫描或删除邻接的历史",
            "首次删除前完成校验",
            "重复运行",
        )

    def test_documents_optional_hardening_and_config_carveout(self) -> None:
        self.assert_readme_contains(
            "--harden-claude",
            "--unharden-claude",
            "合并本 bundle 的 hooks 条目",
            "默认安装不触碰任何配置",
            "settings.json 必须是严格 JSON",
        )

    def test_documents_repository_layout_and_validation(self) -> None:
        self.assert_readme_contains(
            "adapters/claude-code/agents/",
            "claude-code-flow.md",
            "hermes-flow.md",
            "python3 -m unittest discover -s tests -p 'test_*.py'",
            "python3 -m unittest discover -s skills/plan-dev-tasks/tests -p 'test_*.py'",
            "python3 -m unittest discover -s skills/dev-with-tdd/tests -p 'test_*.py'",
            "bash -n install.sh",
            "git diff --check",
        )


if __name__ == "__main__":
    unittest.main()
