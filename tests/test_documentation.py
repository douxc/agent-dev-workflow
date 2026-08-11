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
            "~/.claudeD",
            "~/.claudeP",
            "自动移除旧版遗留",
            "不会代为创建",
            "不创建任何软链接",
            "不产生 `.backup.*`",
        )

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
            "读取时机",
            "创建时机",
            "更新时机",
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

    def test_documents_optional_update_config_dependency(self) -> None:
        self.assert_readme_contains(
            "无硬运行时依赖",
            shared.UPDATE_CONFIG_UNAVAILABLE,
        )

    def test_documents_self_explaining_code_standard(self) -> None:
        self.assert_readme_contains(
            shared.SELF_EXPLAINING_CODE,
            shared.SELF_EXPLAINING_REFERENCE,
            "3 组 Bad/Good 对照",
            shared.CHECK_4_SELF_EXPLAINING,
            shared.POSITIVE_BOOLEAN_NAMING,
        )


if __name__ == "__main__":
    unittest.main()
