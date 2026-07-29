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

    def test_git_packet_context_is_complete_only_for_git_repositories(self) -> None:
        self.assert_all(
            self.skill,
            (
                "Git Context:",
                "Mode: local-only | serial | parallel",
                "Project root:",
                "Remote: none | remote name",
                "Default branch:",
                "Base SHA:",
                "Task branch:",
                "Worktree:",
                "Expected HEAD:",
                "Expected default tip:",
                "Expected remote tip:",
                "Shared dependency paths:",
                "Shared dependency fingerprints:",
                "Git owner: Coordinator",
                "Remote publish authorization: approved | denied",
                "非 Git 项目",
                "不得伪造 `Git Context`",
            ),
        )

    def test_git_context_is_read_only_verified_before_writes(self) -> None:
        self.assert_all(
            self.skill,
            (
                "exact `Worktree`",
                "`git rev-parse --show-toplevel`",
                "`git branch --show-current`",
                "`git rev-parse HEAD`",
                "Coordinator runner `verify`",
                "明确允许写入",
                "写入前",
                "Status: context_gap",
                "实际 worktree、branch 或 HEAD",
                "不得修改任何文件",
            ),
        )

    def test_git_state_writes_belong_only_to_coordinator_runner(self) -> None:
        self.assert_all(
            self.skill,
            (
                "Git 状态写权限只属于 Coordinator shell runner",
                "`status`、`diff`、`log`、`rev-parse`",
                "branch、switch、checkout",
                "worktree add/remove",
                "add、stage、commit",
                "push、pull、fetch",
                "merge、rebase、reset、restore",
                "stash、clean、tag",
                "remote、config",
                "cleanup",
                "不得执行或建议执行",
            ),
        )

    def test_shared_dependencies_are_prepared_read_only_environment(self) -> None:
        self.assert_all(
            self.skill,
            (
                "`Allowed write paths`",
                "共享依赖软链接",
                "不得创建、替换或删除",
                "`Shared dependency paths`",
                "manifest",
                "lockfile",
                "Status: needs_replan",
            ),
        )

    def test_worker_does_not_change_git_mode_or_execution_directory(self) -> None:
        self.assert_all(
            self.skill,
            (
                "serial",
                "parallel",
                "不得自行创建子任务",
                "不得改变执行目录",
                "一次 packet 一个 feature",
            ),
        )

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
                "Git observations:",
                "Worktree:",
                "Branch:",
                "HEAD:",
                "Git state writes: none",
                "Remaining risks:",
                "Status: completed | blocked | context_gap | needs_replan",
                "Language check: passed",
                "只报告观察结果",
                "不得声称已 commit 或 push",
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

    def test_installation_uses_canonical_pair_and_platform_links(self) -> None:
        self.assert_all(
            self.skill,
            (
                "两套 skill 必须成对、同版本安装",
                "`~/.agents/skills/dev-with-tdd` 为 canonical",
                "仅当平台根目录已经存在",
                "`.claude`、`.claudeD`、`.claudeP`、`.codex`、`.hermes`",
                "绝对软链接",
                "不得创建缺失的平台根目录",
                "备份",
            ),
        )
        self.assertNotIn("独立同步副本", self.skill)

    def test_language_contract(self) -> None:
        self.assert_all(self.skill, ("默认使用简体中文", "必要技术字面量"))


if __name__ == "__main__":
    unittest.main()
