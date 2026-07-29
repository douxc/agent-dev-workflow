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
        cls.runtime_path = ROOT / "references/runtime-adapters.md"
        cls.runtime = (
            cls.runtime_path.read_text(encoding="utf-8")
            if cls.runtime_path.exists()
            else ""
        )
        cls.codex_runtime_path = ROOT / "references/runtime-codex.md"
        cls.codex_runtime = (
            cls.codex_runtime_path.read_text(encoding="utf-8")
            if cls.codex_runtime_path.exists()
            else ""
        )
        cls.claude_runtime_path = ROOT / "references/runtime-claude-code.md"
        cls.claude_runtime = (
            cls.claude_runtime_path.read_text(encoding="utf-8")
            if cls.claude_runtime_path.exists()
            else ""
        )
        cls.claude_agent_root = (
            ROOT.parents[1] / "adapters" / "claude-code" / "agents"
        )
        cls.review = read("references/review-checklist.md")
        cls.git_workflow_path = ROOT / "references/git-workflow.md"
        cls.git_workflow = (
            cls.git_workflow_path.read_text(encoding="utf-8")
            if cls.git_workflow_path.exists()
            else ""
        )
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

    def test_git_workflow_is_shell_first_and_fail_closed(self) -> None:
        self.assertTrue(self.git_workflow_path.is_file())
        self.assertIn(
            "[references/git-workflow.md](references/git-workflow.md)",
            self.skill,
        )
        self.assert_all(
            self.git_workflow,
            (
                "`scripts/git-workflow.sh`",
                "prompt 负责决策和结构化参数",
                "状态性 Git 或系统操作",
                "shell runner",
                "fail closed",
                "不得临时拼接",
                "单个只读发现命令",
                "human approval",
                "文件内容编辑",
                "`key<TAB>value`",
                "不得 `eval` 或 `source`",
            ),
        )

    def test_git_repository_syncs_default_branch_before_analysis(self) -> None:
        combined = self.skill + self.git_workflow
        self.assert_all(
            combined,
            (
                "Analysis Brief",
                "`inspect`",
                "`sync`",
                "remote HEAD",
                "`main`",
                "`master`",
                "fast-forward",
                "`Base SHA`",
                "`local-only`",
                "dirty",
                "ahead",
                "diverged",
                "detached",
                "进行中的 Git 操作",
                "不执行 reset、rebase 或 stash",
            ),
        )
        self.assertRegex(
            self.skill,
            r"`inspect`.*Analysis Brief|Analysis Brief.*之前.*`inspect`",
        )

    def test_preapproval_sync_is_the_only_stateful_git_exception(self) -> None:
        combined = self.skill + self.git_workflow
        self.assert_all(
            combined,
            (
                "唯一允许的状态性 Git 例外",
                "feature approval 前",
                "clean default branch",
                "fetch",
                "ff-only",
                "branch、worktree、commit、push",
                "批准前仍禁止",
            ),
        )
        self.assertRegex(
            self.skill,
            r"除.*git-workflow\.md.*inspect.*sync.*唯一.*例外.*批准前只做只读检查",
        )

    def test_git_mode_uses_serial_branch_or_parallel_worktrees(self) -> None:
        combined = self.skill + self.git_workflow + self.workspace
        self.assert_all(
            combined,
            (
                "`prepare-serial`",
                "`prepare-parallel`",
                "同一个 `Base SHA`",
                "依赖串行 packet",
                "共用一条 task branch",
                "当前主 worktree",
                "只调用一次",
                "不创建 worktree",
                "实际同时运行",
                "无依赖",
                "无写入冲突",
                "${PROJECT_ROOT}/.tmp/<task-id>/worktrees/<packet-id>/",
            ),
        )

    def test_parallel_shared_dependencies_are_explicit_and_safe(self) -> None:
        combined = self.git_workflow + self.packet
        self.assert_all(
            combined,
            (
                "Shared dependency paths",
                "`--share`",
                "`node_modules`",
                "目标存在",
                "Git ignored",
                "依赖定义",
                "lockfile",
                "fingerprint",
                "manifest",
                "改为串行",
                "独立安装",
                "构建输出",
                "数据库",
                "运行时状态",
            ),
        )

    def test_packet_carries_versioned_git_context_and_side_effect_authority(self) -> None:
        self.assert_all(
            self.packet,
            (
                "Git Context:",
                "Mode: local-only | serial | parallel",
                "Project root:",
                "Remote:",
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
                "branch、worktree、commit、push",
                "只保留本地 commit",
            ),
        )

    def test_coordinator_owns_verify_commit_drift_and_push_lifecycle(self) -> None:
        combined = self.skill + self.git_workflow + self.review
        self.assert_all(
            combined,
            (
                "worker 写入前",
                "`verify`",
                "`head`",
                "与 `Expected HEAD` 精确匹配",
                "worker handoff",
                "Coordinator 独立 review",
                "`commit`",
                "Allowed write paths",
                "一个 accepted packet 一个 commit",
                "Coordinator metadata commit",
                "完成前再次",
                "默认分支相关路径",
                "共享接口",
                "`context_gap`",
                "重新规划",
                "`push`",
                "expected remote tip",
                "只推送 task branch",
                "不自动 merge",
                "force",
                "共享分支",
                "远端分支",
                "PR/MR",
            ),
        )

    def test_git_state_writes_remain_coordinator_owned(self) -> None:
        combined = self.skill + self.git_workflow + self.packet
        self.assert_all(
            combined,
            (
                "Git owner: Coordinator",
                "worker 不得",
                "branch",
                "worktree",
                "commit",
                "push",
                "merge",
                "rebase",
                "cleanup",
            ),
        )

    def test_parallel_cleanup_is_ordered_and_failure_preserves_state(self) -> None:
        combined = self.skill + self.git_workflow + self.workspace + self.review
        self.assert_all(
            combined,
            (
                "`cleanup-parallel`",
                "accepted commit",
                "clean",
                "先移除 worktree",
                "task workspace",
                "串行模式",
                "失败或 drift",
                "保留现场",
                "正式 diff",
                "任务脚本",
                "日志",
            ),
        )

    def test_readme_documents_provider_neutral_git_workflow(self) -> None:
        readme = read("../../README.md")
        self.assert_all(
            readme,
            (
                "纯 Git workflow",
                "任务开始前",
                "默认分支",
                "串行任务",
                "不创建 worktree",
                "并行任务",
                "受控依赖软链接",
                "shell-first",
                "只推送 task branch",
                "不包含 PR/MR",
            ),
        )
        self.assertNotIn("GitHub", self.git_workflow)
        self.assertNotIn("GitLab", self.git_workflow)

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

    def test_runtime_context_and_worker_record_are_platform_neutral(self) -> None:
        self.assertTrue(self.runtime_path.is_file())
        self.assert_all(
            self.packet + self.runtime,
            (
                "Runtime Context:",
                "Platform: codex | claude-code | hermes",
                "Adapter version:",
                "Worker transport:",
                "Dispatch mode: foreground | background-aggregate",
                "Authorization mode: two-phase | atomic",
                "Completion mode:",
                "Capability evidence:",
                "Worker Record",
                "Task ID",
                "worker handle",
                "Coordinator-only",
                "不得传给 worker",
            ),
        )

    def test_atomic_authorization_evidence_has_one_shared_shape(self) -> None:
        self.assert_all(
            self.packet + self.runtime,
            (
                "Authorization Evidence:",
                "Plan version:",
                "Context version:",
                "Task version:",
                "Task ID:",
                "Environment verification:",
                "Write permission: granted",
                "Git runner verify",
                "non-Git workspace boundary",
                "two-phase",
                "pending",
            ),
        )

    def test_runtime_lifecycle_forces_immediate_review(self) -> None:
        combined = self.skill + self.runtime
        self.assert_all(
            combined,
            (
                "approved",
                "prepared",
                "dispatched",
                "authorized",
                "running",
                "handoff-received",
                "reviewing",
                "accepted",
                "rework",
                "context-gap",
                "blocked",
                "committed",
                "finalized",
                "立即进入 `reviewing`",
                "不得等待普通用户消息唤醒",
                "不得正常结束",
            ),
        )

    def test_shared_dispatch_selects_one_adapter_without_platform_tool_names(self) -> None:
        dispatch = self.skill.split("## 5. 自动调度", 1)[1].split(
            "## 6. 状态处理", 1
        )[0]
        self.assert_all(
            self.skill + self.runtime,
            (
                "Runtime Adapter",
                "只加载",
                "平台信号冲突",
                "fail closed",
            ),
        )
        for platform_tool in (
            "spawn_agent",
            "Agent(dev-with-tdd)",
            "delegate_task",
            "request_user_input",
            "ExitPlanMode",
            "clarify",
        ):
            with self.subTest(platform_tool=platform_tool):
                self.assertNotIn(platform_tool, dispatch)

    def test_codex_runtime_adapter_is_routed_and_capability_gated(self) -> None:
        self.assertTrue(self.codex_runtime_path.is_file())
        self.assertIn(
            "[runtime-codex.md](runtime-codex.md)",
            self.runtime,
        )
        self.assert_all(
            self.codex_runtime,
            (
                "Platform: codex",
                "Adapter version: 1",
                "actually registered",
                "Capability evidence",
                "`spawn_agent`",
                "`send_message`",
                "`followup_task`",
                "`wait_agent`",
                "fail closed",
                "主上下文",
                "冒充 worker",
            ),
        )

    def test_codex_runtime_adapter_requires_two_phase_authorization(self) -> None:
        self.assert_all(
            self.codex_runtime,
            (
                "Authorization mode: two-phase",
                "只读",
                "handshake",
                "Plan version",
                "Context version",
                "Task version",
                "Task ID",
                "Worktree",
                "Task branch",
                "Expected HEAD",
                "Base SHA",
                "Authorization Evidence",
                "同一 worker handle",
            ),
        )

    def test_codex_runtime_adapter_auto_resumes_review_and_aggregates(self) -> None:
        self.assert_all(
            self.codex_runtime,
            (
                "Completion mode: wait_agent/mailbox final handoff",
                "handoff-received",
                "reviewing",
                "立即",
                "普通用户消息",
                "不得正常结束",
                "最多 3",
                "background-aggregate",
                "全部 handoff",
            ),
        )

    def test_codex_runtime_adapter_visibility_and_tool_exclusivity(self) -> None:
        self.assert_all(
            self.codex_runtime,
            (
                "runtime agent tree",
                "`agents/openai.yaml`",
                "`.codex/agents`",
                "不需要",
            ),
        )
        for foreign_tool in (
            "Agent(dev-with-tdd)",
            "Skill(dev-with-tdd)",
            "delegate_task",
            "ExitPlanMode",
            "AskUserQuestion",
            "clarify",
        ):
            with self.subTest(foreign_tool=foreign_tool):
                self.assertNotIn(foreign_tool, self.codex_runtime)

    def test_claude_runtime_adapter_is_routed_and_atomic(self) -> None:
        self.assertTrue(self.claude_runtime_path.is_file())
        self.assertIn(
            "[runtime-claude-code.md](runtime-claude-code.md)",
            self.runtime,
        )
        self.assert_all(
            self.claude_runtime,
            (
                "Platform: claude-code",
                "Adapter version: 1",
                "Worker transport: Agent(dev-with-tdd)",
                "Authorization mode: atomic",
                "`ExitPlanMode`",
                "`AskUserQuestion`",
                "Plan version",
                "Context version",
                "Task version",
                "Task ID",
                "Environment verification",
                "Write permission: granted",
                "派发前",
                "handshake",
                "不等待第二次",
            ),
        )
        self.assertNotIn("Skill(dev-with-tdd)", self.claude_runtime)

    def test_claude_serial_completion_immediately_enters_review(self) -> None:
        self.assert_all(
            self.claude_runtime,
            (
                "Dispatch mode: foreground",
                "Completion mode: foreground Agent result",
                "串行",
                "returned result",
                "handoff-received",
                "reviewing",
                "立即",
                "普通用户消息",
            ),
        )

    def test_claude_parallel_requires_preapproval_aggregation_evidence(self) -> None:
        self.assert_all(
            self.claude_runtime,
            (
                "L3",
                "background-aggregate",
                "最多 3",
                "计划审批前",
                "结果聚合",
                "全部 handoff",
                "串行",
                "批准后",
                "Git mode",
            ),
        )

    def test_claude_adapter_excludes_other_runtime_transports(self) -> None:
        for foreign_tool in (
            "spawn_agent",
            "send_message",
            "followup_task",
            "wait_agent",
            "delegate_task",
            "clarify",
        ):
            with self.subTest(foreign_tool=foreign_tool):
                self.assertNotIn(foreign_tool, self.claude_runtime)

    def test_claude_custom_agents_load_their_corresponding_skills(self) -> None:
        expected = {
            "plan-dev-tasks": (
                "唯一面向用户",
                "Coordinator",
                "Agent(dev-with-tdd)",
            ),
            "dev-with-tdd": (
                "内部实现 worker",
                "Execution Packet",
                "不得",
            ),
        }
        for name, body_markers in expected.items():
            with self.subTest(agent=name):
                path = self.claude_agent_root / f"{name}.md"
                self.assertTrue(path.is_file())
                definition = path.read_text(encoding="utf-8")
                self.assertTrue(definition.startswith("---\n"))
                self.assertRegex(definition, rf"(?m)^name: {re.escape(name)}$")
                self.assertRegex(definition, r"(?m)^model: inherit$")
                self.assertRegex(
                    definition,
                    rf"(?ms)^skills:\n  - {re.escape(name)}$",
                )
                self.assert_all(definition, body_markers)
                self.assertNotIn("permissionMode:", definition)

    def test_claude_installation_boundary_is_explicit(self) -> None:
        self.assert_all(
            self.skill,
            (
                "`~/.agents/platforms/claude-code/agents/`",
                "`.claude`、`.claudeD`、`.claudeP`",
                "`agents/`",
                "`.codex` 和 `.hermes`",
                "不得创建 `agents/`",
                "默认 agent",
                "权限",
                "全局配置",
                "新会话",
                "重启",
                "`/agents`",
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
