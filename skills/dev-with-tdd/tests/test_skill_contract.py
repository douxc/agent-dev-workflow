from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def production_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and "tests" not in path.relative_to(ROOT).parts
        and "__pycache__" not in path.parts
    ]


class DevWithTddContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = read("SKILL.md")
        cls.scope = read("references/tdd-scope.md")
        cls.metadata = read("agents/openai.yaml")
        cls.files = production_files()
        cls.combined = "\n".join(path.read_text(encoding="utf-8") for path in cls.files)

    def assert_all(self, text: str, values: tuple[str, ...]) -> None:
        for value in values:
            with self.subTest(value=value):
                self.assertIn(value, text)

    def test_name_and_internal_worker_role(self) -> None:
        self.assertIsNotNone(re.search(r"^name: dev-with-tdd$", self.skill, re.MULTILINE))
        self.assert_all(
            self.skill,
            (
                "内部执行 worker",
                "一次只执行一个 feature",
                "只接受有效的版本化 Execution Packet",
                "不得接受原始自然语言任务",
                "不自行规划或申请审批",
            ),
        )

    def test_implicit_invocation_is_disabled(self) -> None:
        self.assert_all(
            self.metadata,
            (
                'display_name: "TDD 单任务执行器"',
                "allow_implicit_invocation: false",
            ),
        )

    def test_packet_ack_is_required_before_writes(self) -> None:
        self.assert_all(
            self.skill,
            (
                "Required skill: dev-with-tdd",
                "Approval state: approved",
                "Plan version:",
                "Context version:",
                "Task version:",
                "Task ID:",
                "Loaded skill: dev-with-tdd",
                "Approval inherited: yes",
                "确认完成前不得修改任何文件",
            ),
        )

    def test_packet_is_minimal_complete_context(self) -> None:
        self.assert_all(
            self.skill,
            (
                "Allowed write paths:",
                "Allowed discovery paths:",
                "Forbidden paths:",
                "Forbidden side effects:",
                "Stop conditions:",
                "Project Context:",
                "Relevant map entries:",
                "Applicable constraints:",
                "Local overrides:",
                "Verified source paths:",
                "Relevant tests:",
                "Code evidence:",
                "Workspace Context:",
                "Baseline fingerprint:",
                "Relevant file fingerprints:",
                "Existing user changes:",
                "Red test plan:",
                "Green implementation plan:",
                "Focused verification:",
                "Expanded verification:",
            ),
        )
        self.assert_all(self.skill, ("不得接收完整项目地图", "不得接收完整 transcript"))

    def test_reads_are_bounded_and_writes_are_locked(self) -> None:
        self.assert_all(
            self.skill,
            (
                "Allowed discovery paths",
                "直接依赖",
                "相关测试",
                "适用项目指令",
                "只能修改 `Allowed write paths`",
                "以真实代码为准",
            ),
        )

    def test_context_gap_and_replan_protocols(self) -> None:
        self.assert_all(
            self.skill,
            (
                "Status: context_gap",
                "Missing context:",
                "Why required:",
                "Requested read paths:",
                "Potential write impact:",
                "Approval impact: none | replan_required",
                "Status: needs_replan",
                "不得猜测或扩大范围",
            ),
        )

    def test_executes_tdd_without_internal_delegation(self) -> None:
        combined = self.skill + self.scope
        self.assert_all(
            combined,
            (
                "TDD required",
                "`Red`",
                "`Green`",
                "`Refactor`",
                "不得弱化测试",
                "TDD not required",
            ),
        )
        self.assertNotIn("创建一个实现子任务", combined)
        self.assertNotIn("subagent", combined.lower())

    def test_execution_handoff_is_observational(self) -> None:
        self.assert_all(
            self.skill,
            (
                "Execution Handoff",
                "Changed paths:",
                "Red evidence:",
                "Green verification:",
                "Expanded verification:",
                "Context deviations:",
                "Resource location changes:",
                "Constraint changes observed:",
                "Remaining risks:",
                "Status: completed | blocked | context_gap | needs_replan",
                "Language check: passed",
                "只报告观察结果",
            ),
        )

    def test_dev_has_no_map_coordinator_or_cleanup_responsibilities(self) -> None:
        relative_paths = {str(path.relative_to(ROOT)) for path in self.files}
        self.assertNotIn("references/project-map.md", relative_paths)
        self.assertNotIn("references/task-workspace.md", relative_paths)
        self.assertNotIn("references/review-checklist.md", relative_paths)

        for forbidden in (
            "project-map.md",
            "$plan-dev-tasks",
            "用户直接提交",
            "主 agent 独立审查",
            "更新 Project Map",
            "清理当前任务",
            "创建一个实现子任务",
            "普通 subagent",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.combined)

    def test_language_contract(self) -> None:
        self.assert_all(self.skill, ("默认使用简体中文", "必要技术字面量"))


if __name__ == "__main__":
    unittest.main()
