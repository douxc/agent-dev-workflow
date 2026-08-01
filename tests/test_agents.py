from pathlib import Path
import unittest

import shared


ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "adapters" / "claude-code" / "agents"


class AgentDefinitionTest(unittest.TestCase):
    def read_agent(self, name: str) -> str:
        return (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")

    def test_agent_files_exist_for_both_skills(self) -> None:
        for name in shared.AGENT_NAMES:
            text = self.read_agent(name)
            self.assertTrue(text.startswith("---"))
            self.assertIn(f"name: {name}", text)

    def test_blind_review_agent_is_hard_read_only(self) -> None:
        text = self.read_agent(shared.REVIEW_SKILL)
        self.assertIn("tools: Read, Grep, Glob", text)
        for forbidden in ("Write", "Edit", "Bash", "NotebookEdit"):
            self.assertNotIn(f"tools: {forbidden}", text)

    def test_main_agent_has_no_tools_restriction(self) -> None:
        text = self.read_agent(shared.MAIN_SKILL)
        self.assertNotIn("tools:", text)

    def test_agents_load_their_skills(self) -> None:
        for name in shared.AGENT_NAMES:
            text = self.read_agent(name)
            self.assertIn(f"skills:\n  - {name}", text)

    def test_agents_are_plain_claude_code_frontmatter(self) -> None:
        for name in shared.AGENT_NAMES:
            text = self.read_agent(name)
            self.assertIn("model: inherit", text)
            self.assertTrue(text.rstrip().endswith("---") or "---\n" in text)


if __name__ == "__main__":
    unittest.main()
