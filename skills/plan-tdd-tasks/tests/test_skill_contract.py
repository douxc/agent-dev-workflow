from pathlib import Path
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))
import shared


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
INIT_PATH = ROOT / "references" / "init.md"
INIT_REFERENCE = (
    INIT_PATH.read_text(encoding="utf-8") if INIT_PATH.exists() else ""
)
INIT_TEXT = SKILL + "\n" + INIT_REFERENCE


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

    def test_host_specific_blind_dispatch(self) -> None:
        self.assert_all(
            "Claude Code",
            shared.HERMES_DELEGATE_TASK,
            shared.HERMES_BLIND_READONLY,
            shared.TRANSPORT_UNAVAILABLE,
            shared.TRANSPORT_FAIL_CLOSED,
            shared.TRANSPORT_STOP,
            shared.TRANSPORT_FAIL_CLOSED_RULE,
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
        section = SKILL.split("## 6. 机械范围检查与产出包", 1)[1].split(
            "## 7. 盲测派发", 1
        )[0]
        accidental = section.split(f"**{shared.SCOPE_ACCIDENTAL}**", 1)[1].split(
            f"**{shared.SCOPE_EXPANSION}**", 1
        )[0]
        expansion = section.split(f"**{shared.SCOPE_EXPANSION}**", 1)[1]
        self.assertIn("禁止直接修改 scope.md", section)
        for value in ("保持原 scope", "重新运行本节范围检查", "不重新规划"):
            with self.subTest(branch="accidental", value=value):
                self.assertIn(value, accidental)
        for value in ("先回退越界改动", "回到 §4 重新规划", "再重新实现"):
            with self.subTest(branch="expansion", value=value):
                self.assertIn(value, expansion)

    def test_scope_check_precedes_package_build(self) -> None:
        section = SKILL.split("## 6. 机械范围检查与产出包", 1)[1].split(
            "## 7. 盲测派发", 1
        )[0]
        self.assertIn(shared.SCOPE_BEFORE_PACKAGE, section)
        for package_step in (shared.PACKAGE_BUILD, "构建 `code/`"):
            with self.subTest(package_step=package_step):
                self.assertIn(package_step, section)
                self.assertLess(section.index(shared.SCOPE_BEFORE_PACKAGE),
                                section.index(package_step))

    def test_full_suite_rules(self) -> None:
        self.assert_all(
            "必须覆盖仓库完整测试套件",
            "禁止只跑新增测试",
            "最后执行、恰好 1 遍",
        )

    def test_retry_cap(self) -> None:
        self.assert_all("最多 2 轮", "强制人工", "不得自行开始第 3 轮")

    def test_full_test_failure_rechecks_only_when_package_changes(self) -> None:
        section = SKILL.split("4. 全量测试 FAIL", 1)[1].split(
            "## 10. 重跑上限", 1
        )[0]
        package_change = section.split(
            f"**{shared.FULL_FAIL_PACKAGE_CHANGE}**", 1
        )[1].split(f"**{shared.FULL_FAIL_NO_PACKAGE_CHANGE}**", 1)[0]
        no_package_change = section.split(
            f"**{shared.FULL_FAIL_NO_PACKAGE_CHANGE}**", 1
        )[1]
        for value in ("回到 §6", "§7", "全新盲测者", "轮次 +1"):
            with self.subTest(branch="package-change", value=value):
                self.assertIn(value, package_change)
        for value in (
            "保留上一轮双 PASS",
            "直接重试本节全量测试",
            "不消耗盲测轮次",
        ):
            with self.subTest(branch="no-package-change", value=value):
                self.assertIn(value, no_package_change)

    def test_commit_only_declared_files_once(self) -> None:
        self.assert_all("`git add` 只加范围声明内的文件", "一次 `git commit`")

    def test_final_scope_recheck_follows_map_update_and_precedes_staging(self) -> None:
        section = SKILL.split("## 9. 全量测试与提交", 1)[1].split(
            "## 10. 重跑上限", 1
        )[0]
        self.assertIn(shared.FINAL_SCOPE_RECHECK, section)
        self.assertLess(section.index("run-full-tests: PASS"),
                        section.index(shared.FINAL_SCOPE_RECHECK))
        self.assertLess(section.index("先更新对应小节"),
                        section.index(shared.FINAL_SCOPE_RECHECK))
        self.assertLess(section.index(shared.FINAL_SCOPE_RECHECK),
                        section.index("`git add`"))

    def test_environment_only_retry_has_manual_exit(self) -> None:
        section = SKILL.split(
            f"**{shared.FULL_FAIL_NO_PACKAGE_CHANGE}**", 1
        )[1].split("## 10. 重跑上限", 1)[0]
        self.assertIn(shared.ENV_RETRY_CAP, section)
        self.assertIn("连续失败后停止并转人工处理", section)

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
        for value in ("读取时机", "更新时机", "文件不存在"):
            with self.subTest(value=value):
                self.assertIn(value, SKILL)
        self.assertIn("创建时机", INIT_REFERENCE)

    def test_normal_task_does_not_create_or_globally_drift_check_map(self) -> None:
        analysis = SKILL.split("## 3. 分析", 1)[1].split("## 4. 规划", 1)[0]
        timing = SKILL.split("### 11.4 时机", 1)[1].split(
            "## 12. init 模式", 1
        )[0]
        for value in (
            shared.PROJECT_MAP_INIT_HINT,
            "普通任务不创建地图",
            shared.PROJECT_MAP_NO_GLOBAL_DRIFT,
        ):
            with self.subTest(value=value):
                self.assertIn(value, analysis)
        self.assertIn("只提示运行 `/plan-tdd-tasks init`", timing)
        self.assertNotIn("创建时机 | §3", timing)
        self.assertNotIn("漂移判定 | §3", timing)

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

    def test_cross_reference_corrections(self) -> None:
        self.assertIn("§9 最终提交与 §12 init 收尾提交是仅有的例外", SKILL)
        self.assertIn("全量留给 §9", SKILL)
        self.assertNotIn("§8 最终提交", SKILL)
        self.assertNotIn("全量留给 §7", SKILL)

    def test_init_mode_markers(self) -> None:
        self.assert_all(shared.INIT_TRIGGER, shared.INIT_NOT_A_TASK,
                        shared.INIT_REFERENCE)
        for value in (shared.INIT_PERMISSION, shared.INIT_COMMIT):
            with self.subTest(value=value):
                self.assertIn(value, INIT_REFERENCE)

    def test_init_reference_exists_and_owns_detailed_flow(self) -> None:
        self.assertTrue(INIT_PATH.is_file())
        self.assertIn("地图", INIT_REFERENCE)
        self.assertIn("gitignore", INIT_REFERENCE)
        self.assertIn("权限", INIT_REFERENCE)
        self.assertNotIn("### 12.3 步骤", SKILL)

    def test_init_update_config_unavailable_is_non_blocking(self) -> None:
        self.assertIn(shared.UPDATE_CONFIG_UNAVAILABLE, INIT_REFERENCE)
        self.assertIn("继续其余步骤", INIT_REFERENCE)

    def test_init_drift_check_and_update(self) -> None:
        for value in (
            shared.INIT_DRIFT_CHECK,
            shared.INIT_DRIFT_UPDATE_CONSENT,
            shared.INIT_DRIFT_REFUSE_SKIP,
            shared.INIT_DRIFT_MECHANICAL,
            shared.INIT_DRIFT_NO_STYLE,
            shared.INIT_DRIFT_NO_UPDATE,
            shared.INIT_DRIFT_TABLE_ROW,
            shared.INIT_UPDATE_COMMIT,
        ):
            with self.subTest(value=value):
                self.assertIn(value, INIT_REFERENCE)
        self.assertNotIn("跳过生成并报告（漂移更新仍在任务流程",
                         INIT_TEXT)

    def test_tdd_red_has_no_unverifiable_record_ritual(self) -> None:
        self.assertIn(shared.RED_CAUSE, SKILL)
        self.assertNotIn(shared.RED_RECORD, SKILL)


if __name__ == "__main__":
    unittest.main()
