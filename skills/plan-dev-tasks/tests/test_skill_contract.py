from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class PlanDevTasksContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = read("SKILL.md")
        cls.map_ref = read("references/project-map.md")
        cls.workspace = read("references/task-workspace.md")
        cls.packet = read("references/task-packet.md")
        cls.review = read("references/review-checklist.md")
        cls.approval_path = ROOT / "references/human-approval.md"
        cls.approval = (
            cls.approval_path.read_text(encoding="utf-8")
            if cls.approval_path.exists()
            else ""
        )
        cls.metadata = read("agents/openai.yaml")

    def assert_all(self, text: str, values: tuple[str, ...]) -> None:
        for value in values:
            with self.subTest(value=value):
                self.assertIn(value, text)

    def test_name_user_entry_and_coordinator_role(self) -> None:
        self.assertIsNotNone(re.search(r"^name: plan-dev-tasks$", self.skill, re.MULTILINE))
        self.assert_all(
            self.skill + self.metadata,
            (
                "唯一面向用户和隐式触发的开发入口",
                "Coordinator",
                "allow_implicit_invocation: true",
                "不实现业务代码",
            ),
        )

    def test_grading_and_single_approval(self) -> None:
        self.assert_all(
            self.skill + self.packet,
            (
                "L1 atomic",
                "L2 compound",
                "L3 task package",
                "同一版本化任务包只申请一次 human approval",
                "批准并继续 (Recommended)",
                "Approval state: approved",
            ),
        )

    def test_human_approval_reference_replaces_generic_fallback(self) -> None:
        self.assertTrue(self.approval_path.is_file())
        self.assertIn(
            "[references/human-approval.md](references/human-approval.md)",
            self.skill,
        )
        self.assertNotIn(
            "优先使用平台原生结构化选择；不可用时才要求文本回复",
            self.skill,
        )

    def test_human_approval_platform_detection_is_explicit_and_fail_closed(self) -> None:
        self.assert_all(
            self.approval,
            (
                "当前工具注册表",
                "运行时元数据",
                "不得通过 `HOME` 目录",
                "平台签名冲突",
                "未知平台",
                "unsupported platform",
                "conflicting platform",
                "fail closed",
                "不得使用共享通用审批",
            ),
        )

    def test_codex_approval_uses_request_user_input_or_exact_default_text(self) -> None:
        self.assert_all(
            self.approval,
            (
                "Codex",
                "`request_user_input`",
                "当前可用",
                "只能调用一次",
                "单选",
                "不得设置 `autoResolutionMs`",
                "Default mode",
                "Codex 专属精确文本选择",
                "`批准并继续`",
                "`修改计划`",
                "`取消任务`",
                "不得自动批准",
            ),
        )

    def test_codex_default_exact_text_is_the_only_free_text_exception(self) -> None:
        self.assert_all(
            self.approval,
            (
                "第 3 节 Codex Default mode 的精确文本选择除外",
                "`批准并继续` → `approved`",
                "`修改计划` → `revise`",
                "`取消任务` → `cancel`",
                "其他任何自由文本",
            ),
        )

    def test_claude_code_approval_uses_plan_specific_tools(self) -> None:
        self.assert_all(
            self.approval,
            (
                "Claude Code",
                "`ExitPlanMode`",
                "Plan mode",
                "`AskUserQuestion`",
                "非 Plan",
                "非交互宿主",
                "`blocked`",
                "不得借用 Codex 或 Hermes",
            ),
        )
        self.assertRegex(
            self.approval,
            r"Plan mode.*`ExitPlanMode`|`ExitPlanMode`.*Plan mode",
        )

    def test_hermes_approval_uses_clarify_not_command_approval(self) -> None:
        self.assert_all(
            self.approval,
            (
                "Hermes",
                "`clarify`",
                "`clarify.respond`",
                "`approval.request`",
                "`approval.respond`",
                "危险命令",
                "未注册",
                "`blocked`",
            ),
        )
        self.assertRegex(
            self.approval,
            r"不得[^。\n]*`approval\.request`[^。\n]*`approval\.respond`",
        )

    def test_platform_approval_branches_forbid_cross_tool_fallback(self) -> None:
        self.assert_all(
            self.approval,
            (
                "Codex 分支不得调用 Claude Code 或 Hermes 工具",
                "Claude Code 分支不得借用 Codex 或 Hermes 的审批入口",
                "Hermes 分支不得调用 Codex 或 Claude Code 工具",
            ),
        )

    def test_approval_decision_is_authenticated_versioned_and_single_use(self) -> None:
        self.assert_all(
            self.approval,
            (
                "`approved | revise | cancel | blocked`",
                "`Plan version`",
                "`Context version`",
                "`Task version`",
                "只有 `approved`",
                "沉默",
                "超时",
                "工具拒绝",
                "模糊回答",
                "同一版本只请求一次审批",
            ),
        )

    def test_project_map_is_coordinator_owned_lookup_input(self) -> None:
        combined = self.skill + self.map_ref
        self.assert_all(
            combined,
            (
                "${PROJECT_ROOT}/project-map.md",
                "# Project Map",
                "lookup-first",
                "代码、测试和仓库指令是事实来源",
                "Coordinator 是唯一写入者",
                "worker 不得读取完整地图",
                "同一 key",
            ),
        )
        self.assertNotIn("project-memory.md", combined)

    def test_packet_is_minimal_complete_execution_context(self) -> None:
        self.assert_all(
            self.packet,
            (
                "Required skill: dev-with-tdd",
                "Approval state: pending | approved",
                "Plan version:",
                "Context version:",
                "Task version:",
                "Task ID:",
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
                "TDD classification:",
                "Red test plan:",
                "Green implementation plan:",
                "Focused verification:",
                "Expanded verification:",
            ),
        )
        self.assert_all(
            self.packet,
            (
                "不得包含完整 `project-map.md`",
                "不得包含完整 agent transcript",
            ),
        )

    def test_current_main_agent_must_dispatch_workers(self) -> None:
        self.assert_all(
            self.skill,
            (
                "当前主 agent 必须自动调度",
                "不得交给未定义的外部调度器",
                "每个 packet 只派发给一个 `$dev-with-tdd` worker",
                "`L1` 和 `L2` 串行派发",
                "`L3`",
                "最多 3 个 worker",
                "依赖已经完成",
                "写入路径不冲突",
            ),
        )

    def test_dispatch_requires_ack_before_worker_writes(self) -> None:
        self.assert_all(
            self.skill,
            (
                "Required skill: dev-with-tdd",
                "Loaded skill: dev-with-tdd",
                "Approval inherited: yes",
                "确认版本一致",
                "未确认时不得允许修改",
                "不得接受 handoff",
            ),
        )

    def test_handoff_context_gap_and_replan_handling(self) -> None:
        self.assert_all(
            self.skill,
            (
                "Status: context_gap",
                "Missing context:",
                "Requested read paths:",
                "Approval impact: none | replan_required",
                "Status: needs_replan",
                "只读上下文补充",
                "更新 `Context version`",
                "重新规划并使旧批准失效",
            ),
        )

    def test_final_review_map_decision_and_cleanup_are_coordinator_owned(self) -> None:
        combined = self.skill + self.review + self.workspace + self.map_ref
        self.assert_all(
            combined,
            (
                "Coordinator 独立 review",
                "实际 diff",
                "Red",
                "Green",
                "没有越界",
                "过度设计",
                "UI/UX",
                "Resource location changes",
                "Constraint changes observed",
                "只按受影响 key",
                "代码与地图均已持久化",
                "失败、`context_gap`、blocked 或地图冲突时保留",
                "清理当前任务目录",
            ),
        )

    def test_global_scan_is_explicit_and_bounded(self) -> None:
        combined = self.skill + self.map_ref
        self.assert_all(
            combined,
            (
                "只有用户明确要求",
                "全局扫描生成地图",
                "刷新项目地图",
                "rg --files",
                "选择性读取",
                "全局扫描不等于把每个文件完整载入上下文",
                "Git ignored",
            ),
        )

    def test_workspace_and_gitignore_contract(self) -> None:
        self.assert_all(
            self.workspace,
            (
                "${PROJECT_ROOT}/.tmp/<task-id>/",
                "根目录 `.gitignore`",
                "`/.tmp/`",
                "`task-owner.json`",
                "软链接逃逸",
                "删除其他任务或用户文件",
            ),
        )
        self.assertNotIn("/private/tmp", self.skill + self.workspace)

    def test_installation_uses_canonical_pair_and_platform_links(self) -> None:
        self.assert_all(
            self.skill,
            (
                "两套 skill 必须成对、同版本安装",
                "`~/.agents/skills/plan-dev-tasks` 为 canonical",
                "仅当平台根目录已经存在",
                "`.claude`、`.claudeD`、`.claudeP`、`.codex`、`.hermes`",
                "绝对软链接",
                "不得创建缺失的平台根目录",
                "备份",
            ),
        )
        self.assertNotIn("独立同步副本", self.skill)

    def test_language_contract(self) -> None:
        self.assert_all(self.skill + self.packet + self.review, ("默认使用简体中文", "Language check: passed"))


if __name__ == "__main__":
    unittest.main()
