from pathlib import Path
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))
import shared


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")


class PlanTddTasksContractTest(unittest.TestCase):
    def assert_all(self, *values: str) -> None:
        for value in values:
            with self.subTest(value=value):
                self.assertIn(value, SKILL)

    def test_flow_phases_and_scope(self) -> None:
        self.assert_all(
            "分析",
            "规划",
            "TDD 实现与自测",
            "盲测 ×2",
            "全量测试",
            "一次只处理一个 feature",
        )

    def test_planning_never_persisted(self) -> None:
        self.assert_all("规划不落盘", "只存在于对话中")

    def test_no_commit_or_stage_until_final(self) -> None:
        self.assert_all("不得执行 `git commit`", "不得执行 `git add`/stage")

    def test_ac_grammar_markers(self) -> None:
        self.assert_all(shared.AC_HEADER, shared.AC_ITEM, shared.AC_ASSERT,
                        shared.AC_OWNER, shared.AC_VERIFY)
        for value in shared.AC_VERIFY_VALUES:
            self.assertIn(value, SKILL)
        for word in shared.AC_BANNED_WORDS:
            self.assertIn(word, SKILL)  # 禁词表本身出现在 skill 文本中
        self.assertIn("禁止复合 AC", SKILL)

    def test_scope_statement_markers_and_freeze(self) -> None:
        self.assert_all(shared.SCOPE_MARKER_FILES, shared.SCOPE_MARKER_INFRA,
                        "约束:", "实现前写定", "事后禁止修补")
        self.assertIn("不得事后修补以匹配实际改动", SKILL)

    def test_scripts_absolute_path_invocations(self) -> None:
        self.assert_all(
            f"{shared.SCRIPT_CHECK_SCOPE} {shared.FLAG_PROJECT_ROOT} "
            f"<PROJECT_ROOT> {shared.FLAG_SCOPE_FILE} <package>/scope.md "
            f"{shared.FLAG_BASE} <base>",
            f"{shared.SCRIPT_RUN_FULL_TESTS} {shared.FLAG_PROJECT_ROOT} "
            f"<PROJECT_ROOT> {shared.FLAG_TEST_CMD} \"$(cat <package>/"
            f"test-command.txt)\"",
            "${SKILL_ROOT}/scripts/check-scope.sh",
            "${SKILL_ROOT}/scripts/run-full-tests.sh",
            "绝对路径调用",
        )

    def test_package_layout(self) -> None:
        for item in shared.PACKAGE_FILES:
            self.assertIn(item, SKILL)

    def test_blind_dispatch_and_blindness(self) -> None:
        self.assert_all(
            "Agent(blind-review-tasks)",
            "同一条消息",
            "并行",
            "全新上下文",
            "传递任何设计意图",
        )

    def test_disagreement_handling(self) -> None:
        self.assert_all(
            "双 fail",
            "禁止反驳",
            "一 pass 一 fail",
            "自辩",
            "呈交用户仲裁",
        )

    def test_scope_violation_reverts_before_replanning(self) -> None:
        self.assert_all("先回退越界改动", "回到 §4 重新规划", "禁止直接修改 scope.md")

    def test_full_suite_rules(self) -> None:
        self.assert_all(
            "必须覆盖仓库完整测试套件",
            "禁止只跑新增测试",
            "最后执行、恰好 1 遍",
        )

    def test_retry_cap(self) -> None:
        self.assert_all("最多 2 轮", "强制人工", "不得自行开始第 3 轮")

    def test_full_test_failure_restarts_blind_review(self) -> None:
        self.assertIn("回到 §7 重新派发全新盲测者", SKILL)

    def test_commit_only_declared_files_once(self) -> None:
        self.assert_all("`git add` 只加范围声明内的文件", "一次 `git commit`")

    def test_project_map_semantics(self) -> None:
        self.assert_all(
            shared.PROJECT_MAP,
            "项目地图",
            "快速熟悉项目",
            "确认变更文件",
            "索引",
            "有价值",
            "项目元数据",
            "非规划产物",
        )
        for section in shared.PM_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, SKILL)

    def test_project_map_timing(self) -> None:
        self.assert_all("读取时机", "创建时机", "更新时机", "文件不存在")

    def test_project_map_scope_interaction(self) -> None:
        self.assert_all(
            "列入范围声明 `infra:`",
            "不复制进 `code/`",
            "盲测者不读取 project-map.md",
            "前后端分离",
            "前后端一体",
            "取舍",
        )

    def test_project_map_not_a_planner_state(self) -> None:
        self.assertIn("无状态机、无版本号、无 gates", SKILL)
        self.assertNotIn("无 project map", SKILL)


if __name__ == "__main__":
    unittest.main()
