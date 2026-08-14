from pathlib import Path
import unittest

import shared


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

    def test_documents_two_skills_and_their_roles(self) -> None:
        self.assert_readme_contains(
            "plan-tdd-tasks",
            "blind-review-tasks",
            "全流程主 agent",
            "纯只读、无执行环境的静态盲审复核者",
        )

    def test_documents_workflow_phases(self) -> None:
        self.assert_readme_contains(
            "分析",
            "规划",
            "TDD 实现与自测",
            "机械范围检查",
            "盲测 ×2",
            "分歧处理",
            "全量测试",
            "一次 commit",
        )

    def test_documents_retirement_of_legacy(self) -> None:
        self.assert_readme_contains(
            "已整体退役并删除",
            "从零重建",
        )

    def test_documents_retry_cap_and_disagreement(self) -> None:
        self.assert_readme_contains(
            "最多 2 轮",
            "强制人工",
            "双 fail",
            "禁反驳",
            "自辩",
            "用户仲裁",
        )

    def test_documents_ac_grammar(self) -> None:
        self.assert_readme_contains(
            shared.AC_HEADER,
            shared.AC_ITEM,
            shared.AC_ASSERT,
            shared.AC_OWNER,
            shared.AC_VERIFY,
            "禁止复合 AC",
        )
        for word in shared.AC_BANNED_WORDS:
            self.assertIn(word, self.readme)

    def test_documents_scope_statement_and_freeze(self) -> None:
        self.assert_readme_contains(
            shared.SCOPE_MARKER_FILES,
            shared.SCOPE_MARKER_INFRA,
            "实现前写定，事后禁止修补",
            "先回退越界改动",
            shared.SCOPE_ACCIDENTAL,
            shared.SCOPE_EXPANSION,
        )

    def test_documents_deduplicated_failure_paths(self) -> None:
        self.assert_readme_contains(
            shared.SCOPE_BEFORE_PACKAGE,
            shared.FULL_FAIL_PACKAGE_CHANGE,
            shared.FULL_FAIL_NO_PACKAGE_CHANGE,
            shared.PROJECT_MAP_INIT_HINT,
            shared.PROJECT_MAP_NO_GLOBAL_DRIFT,
            shared.INIT_REFERENCE,
            shared.FINAL_SCOPE_RECHECK,
            shared.ENV_RETRY_CAP,
        )

    def test_documents_blind_phase_test_execution_and_skip(self) -> None:
        self.assert_readme_contains(
            "package/test-run.log",
            "字面 `SKIP`",
            "主动询问用户是否跳过测试执行",
            "最终门禁",
        )

    def test_documents_script_interfaces_and_exit_codes(self) -> None:
        self.assert_readme_contains(
            shared.SCRIPT_CHECK_SCOPE,
            shared.SCRIPT_RUN_FULL_TESTS,
            shared.FLAG_PROJECT_ROOT,
            shared.FLAG_SCOPE_FILE,
            shared.FLAG_BASE,
            shared.FLAG_TEST_CMD,
            shared.FLAG_WORKDIR,
            shared.FLAG_LOG_FILE,
            shared.SCOPE_CHECK_PASS,
            shared.SCOPE_CHECK_FAIL,
            shared.RUN_FULL_TESTS_PASS,
            shared.RUN_FULL_TESTS_FAIL,
            shared.RUN_FULL_TESTS_USAGE,
        )

    def test_documents_installation_and_legacy_removal(self) -> None:
        self.assert_readme_contains(
            "./install.sh",
            "~/.claude",
            "~/.claudeP",
            "（`~/.claude`、`~/.claudeP`）",
            "自动移除旧版遗留",
            "已废弃的 `~/.claudeD` 平台根（若存在）被整体移除",
            "不会代为创建",
            "不创建任何软链接",
            "不产生 `.backup.*`",
        )

    def test_documents_user_settings_merge(self) -> None:
        self.assert_readme_contains(
            "~/.claude/settings.json",
            "permissions.allow",
            shared.INIT_PERMISSION_HOME_CLAUDE,
            shared.INIT_PERMISSION_HOME_CLAUDE_P,
            "`python3` 不可用时输出 warning 并继续",
            "`-p` 模式不触碰用户级 settings",
        )

    def test_documents_init_permission_gate(self) -> None:
        self.assert_readme_contains(
            shared.INIT_PERMISSION_GATE,
            "权限步骤必须先完成",
        )

    def test_platforms_contract(self) -> None:
        self.assertEqual(shared.PLATFORMS, (".claude", ".claudeP"))
        self.assert_readme_contains("~/.claude", "~/.claudeP")

    def test_platform_assertions_omit_bare_clauded(self) -> None:
        bare_item = '"~/.claudeD"' + ","
        own = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn(bare_item, own)

    def test_documents_package_layout(self) -> None:
        for item in shared.PACKAGE_FILES:
            self.assertIn(item, self.readme)

    def test_documents_validation_commands(self) -> None:
        self.assert_readme_contains(
            "python3 -m unittest discover -s tests -p 'test_*.py'",
            "python3 -m unittest discover -s skills/plan-tdd-tasks/tests -p 'test_*.py'",
            "python3 -m unittest discover -s skills/blind-review-tasks/tests -p 'test_*.py'",
            "bash -n install.sh",
            "bash -n skills/plan-tdd-tasks/scripts/check-scope.sh",
            "git diff --check",
        )
        self.assertNotIn(
            "\nsh -n skills/plan-tdd-tasks/scripts/check-scope.sh",
            self.readme,
        )

    def test_documents_project_map(self) -> None:
        self.assert_readme_contains(
            shared.PROJECT_MAP,
            "架构",
            "选型",
            "普通任务只读",
            "地图创建和更新",
            shared.PM_INIT_ONLY_UPDATE,
        )

    def test_log_location_in_layout(self) -> None:
        self.assertIn("rebuttal.md（仅分歧时）", self.readme)
        self.assertIn("└── full-tests.log", self.readme)
        self.assertNotIn("仅分歧时）, full-tests.log", self.readme)

    def test_documents_init_mode(self) -> None:
        self.assert_readme_contains(
            shared.INIT_TRIGGER,
            shared.INIT_NOT_A_TASK,
            shared.INIT_PERMISSION,
            shared.INIT_COMMIT,
        )

    def test_documents_init_drift_check(self) -> None:
        self.assert_readme_contains(
            shared.INIT_DRIFT_CHECK,
            shared.INIT_DRIFT_UPDATE_CONSENT,
            shared.INIT_DRIFT_NO_UPDATE,
            shared.INIT_UPDATE_COMMIT,
        )

    def test_documents_fast_navigation_and_bounded_analysis(self) -> None:
        self.assert_readme_contains(
            shared.PM_FAST_INDEX,
            shared.PM_NAV_CANDIDATE,
            shared.PM_INDEX_NO_SOURCE,
            shared.PM_ANALYSIS_CHECKPOINT,
            shared.PM_CONTINUE_WINDOW,
            shared.PM_ACCEPT_CONFIRMED_ONLY,
            shared.PM_NOT_SCOPE_PROOF,
        )

    def test_documents_manual_init_only_domain_navigation(self) -> None:
        self.assert_readme_contains(
            shared.PM_INIT_ONLY_UPDATE,
            shared.PM_DOMAIN_OBJECT,
            shared.PM_DIRECT_PRODUCER,
            shared.PM_DIRECT_CONSUMER,
            shared.PM_ONE_HOP,
            "数据库结构不能单独证明生产者",
            "不确定的关系直接省略",
        )

    def test_documents_hermes_profile_install(self) -> None:
        self.assert_readme_contains(
            shared.FLAG_PROFILE,
            shared.HERMES_PROFILES_DIR,
            shared.INSTALL_PROFILE_EXCLUSIVE,
            shared.HERMES_BLIND_READONLY,
            shared.HERMES_DELEGATE_TASK,
            shared.TRANSPORT_UNAVAILABLE,
            shared.TRANSPORT_FAIL_CLOSED,
            shared.TRANSPORT_STOP,
        )

    def test_documents_init_permission_template(self) -> None:
        self.assert_readme_contains(
            shared.INIT_PERMISSION_TEMPLATE,
            shared.INIT_PERMISSION,
            shared.INIT_PERMISSION_EDIT_ROOT,
            shared.INIT_PERMISSION_BASELINE,
            shared.INIT_PERMISSION_GIT_ALL,
            shared.INIT_PERMISSION_HOME_CLAUDE,
            shared.INIT_PERMISSION_HOME_CLAUDE_P,
        )

    def test_documents_optional_update_config_dependency(self) -> None:
        self.assert_readme_contains(
            "无硬运行时依赖",
            shared.UPDATE_CONFIG_UNAVAILABLE,
        )

    def test_documents_self_explaining_code_standard(self) -> None:
        self.assert_readme_contains(
            shared.SELF_EXPLAINING_CODE,
            shared.SELF_EXPLAINING_REFERENCE,
            "4 组 Bad/Good 对照",
            "只审查本次变更中的人工编写代码",
            shared.CHECK_4_SELF_EXPLAINING,
            shared.POSITIVE_BOOLEAN_NAMING,
        )
        self.assertNotIn("3 组 Bad/Good 对照", self.readme)

    def test_documents_branch_policy(self) -> None:
        self.assert_readme_contains(
            shared.BRANCH_PROTECTED_MAIN,
            shared.BRANCH_FEATURE_BRANCH,
            shared.BRANCH_NO_PERSISTENT_DEV,
            shared.BRANCH_COMMIT_ON_BRANCH,
            shared.BRANCH_USER_MERGE,
            shared.BRANCH_DELETE_AFTER_MERGE,
            "最终提交必须落在临时分支",
        )
        self.assertNotIn("deploy/test", self.readme)
        self.assertNotIn("基于 dev 分支", self.readme)

    def test_documents_mechanical_gate_scripts(self) -> None:
        self.assert_readme_contains(
            "准入闸门",
            shared.SCRIPT_CHECK_ENV,
            shared.SCRIPT_VALIDATE_AC,
            shared.SCRIPT_PARSE_VERDICT,
            shared.ENV_CHECK_PASS,
            shared.AC_CHECK_PASS,
            shared.VERDICT_PARSE_PASS,
            shared.VERDICT_PARSE_FAIL,
            shared.VERDICT_PARSE_MALFORMED,
        )

    def test_documents_gate_validation_commands(self) -> None:
        self.assert_readme_contains(
            "bash -n skills/plan-tdd-tasks/scripts/check-env.sh",
            "bash -n skills/plan-tdd-tasks/scripts/validate-ac.sh",
            "bash -n skills/plan-tdd-tasks/scripts/parse-verdict.sh",
        )

    def test_documents_mechanical_workflow_scripts(self) -> None:
        self.assert_readme_contains(
            shared.SCRIPT_BUILD_PACKAGE,
            shared.SCRIPT_STAGE_SCOPE,
            shared.SCRIPT_DECIDE_VERDICTS,
            shared.FLAG_LIST_CHANGED,
            shared.FLAG_PACKAGE,
            shared.FLAG_MESSAGE,
            shared.FLAG_VERDICT_A,
            shared.FLAG_VERDICT_B,
            shared.BUILD_PACKAGE_PASS,
            shared.STAGE_SCOPE_PASS,
            shared.STAGE_SCOPE_SKIP,
            shared.DECIDE_DOUBLE_PASS,
            shared.DECIDE_DOUBLE_FAIL,
            shared.DECIDE_SPLIT,
            shared.DECIDE_MALFORMED,
            shared.NEW_FILE_MARKER,
            "M|<path>",
            "N|<path>",
            "stdout 即数据（无状态行）",
            "恰好一次 `git commit -m <msg>`",
        )

    def test_documents_workflow_script_validation_commands(self) -> None:
        self.assert_readme_contains(
            "bash -n skills/plan-tdd-tasks/scripts/build-package.sh",
            "bash -n skills/plan-tdd-tasks/scripts/stage-scope.sh",
            "bash -n skills/plan-tdd-tasks/scripts/decide-verdicts.sh",
        )


if __name__ == "__main__":
    unittest.main()
