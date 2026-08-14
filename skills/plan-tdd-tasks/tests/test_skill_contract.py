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
SELF_EXPLAINING_PATH = ROOT / "references" / "self-explaining-code.md"
SELF_EXPLAINING_REFERENCE = (
    SELF_EXPLAINING_PATH.read_text(encoding="utf-8")
    if SELF_EXPLAINING_PATH.exists()
    else ""
)
PERMISSION_PATH = ROOT / "references" / "permission-template.md"
PERMISSION_TEMPLATE = (
    PERMISSION_PATH.read_text(encoding="utf-8")
    if PERMISSION_PATH.exists()
    else ""
)
AGENT_PATH = (
    Path(__file__).resolve().parents[3]
    / "adapters" / "claude-code" / "agents" / "plan-tdd-tasks.md"
)
AGENT = (
    AGENT_PATH.read_text(encoding="utf-8") if AGENT_PATH.exists() else ""
)


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

    def test_final_scope_recheck_precedes_staging(self) -> None:
        section = SKILL.split("## 9. 全量测试与提交", 1)[1].split(
            "## 10. 重跑上限", 1
        )[0]
        self.assertIn(shared.FINAL_SCOPE_RECHECK, section)
        self.assertLess(section.index("run-full-tests: PASS"),
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

    def test_analysis_uses_fast_map_navigation_before_source_exploration(self) -> None:
        analysis = SKILL.split("## 3. 分析", 1)[1].split("## 4. 规划", 1)[0]
        for value in (
            shared.PM_FAST_INDEX,
            shared.PM_NAV_CANDIDATE,
            shared.PM_INDEX_NO_SOURCE,
            "只搜索一次 `project-map.md`",
            "地图未命中",
        ):
            with self.subTest(value=value):
                self.assertIn(value, analysis)
        self.assertLess(
            analysis.index(shared.PM_FAST_INDEX),
            analysis.index("源码分析"),
        )

    def test_analysis_has_five_minute_human_checkpoint(self) -> None:
        analysis = SKILL.split("## 3. 分析", 1)[1].split("## 4. 规划", 1)[0]
        for value in (
            shared.PM_ANALYSIS_CHECKPOINT,
            "已确认",
            "已排除",
            "未确认",
            "残余风险",
            shared.PM_CONTINUE_WINDOW,
            shared.PM_ACCEPT_CONFIRMED_ONLY,
        ):
            with self.subTest(value=value):
                self.assertIn(value, analysis)

    def test_project_map_is_navigation_not_scope_proof(self) -> None:
        project_map = SKILL.split("## 11. project-map.md", 1)[1].split(
            "## 12. init 模式", 1
        )[0]
        self.assertIn(shared.PM_NOT_SCOPE_PROOF, project_map)
        self.assertIn("粗粒度", project_map)
        self.assertIn("不得记录与代码证据冲突的关系", project_map)

    def test_project_map_timing(self) -> None:
        for value in ("读取时机", "创建与更新", "文件不存在"):
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
            "普通任务不创建或更新地图",
            shared.PROJECT_MAP_NO_GLOBAL_DRIFT,
        ):
            with self.subTest(value=value):
                self.assertIn(value, analysis)
        self.assertIn("只提示运行 `/plan-tdd-tasks init`", timing)
        self.assertNotIn("创建时机 | §3", timing)
        self.assertNotIn("漂移判定 | §3", timing)
        self.assertNotIn("更新时机 | §9", timing)
        self.assertIn(shared.PM_INIT_ONLY_UPDATE, timing)

    def test_project_map_scope_interaction(self) -> None:
        self.assert_all(
            "不复制进 `code/`",
            "盲测者不读取 project-map.md",
            "前后端分离",
            "前后端一体",
            "取舍",
        )
        self.assertNotIn("列入范围声明 `infra:`", SKILL)

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

    def test_init_generates_high_confidence_one_hop_domain_navigation(self) -> None:
        for value in (
            shared.PM_DOMAIN_OBJECT,
            shared.PM_DIRECT_PRODUCER,
            shared.PM_DIRECT_CONSUMER,
            shared.PM_ONE_HOP,
            "数据库结构不能单独证明生产者",
            "不确定的关系直接省略",
        ):
            with self.subTest(value=value):
                self.assertIn(value, INIT_REFERENCE)

    def test_init_permission_template_file_exists(self) -> None:
        self.assertTrue(PERMISSION_PATH.is_file())

    def test_init_permission_template_groups_and_placeholder(self) -> None:
        for value in (
            shared.INIT_PERMISSION,
            shared.INIT_PERMISSION_EDIT_ROOT,
            shared.INIT_PERMISSION_BASELINE,
            shared.INIT_PERMISSION_PER_LANGUAGE,
            shared.INIT_PERMISSION_GIT_ALL,
            *shared.INIT_SHELL_ALLOW,
            shared.INIT_PERMISSION_HOME_CLAUDE,
            shared.INIT_PERMISSION_HOME_CLAUDE_P,
            "WebSearch",
            "WebFetch",
            "Bash(python3 -m unittest:*)",
            "Bash(npm test:*)",
            "Bash(cargo test:*)",
            "Bash(go test:*)",
        ):
            with self.subTest(value=value):
                self.assertIn(value, PERMISSION_TEMPLATE)
        self.assertNotIn("WebFetch(", PERMISSION_TEMPLATE)
        self.assertNotIn("ask：变更类", PERMISSION_TEMPLATE)

    def test_init_permission_step_references_template(self) -> None:
        self.assertIn(shared.INIT_PERMISSION_TEMPLATE, INIT_REFERENCE)
        self.assertIn(shared.INIT_PERMISSION, INIT_REFERENCE)
        self.assertNotIn("ask：变更类", INIT_REFERENCE)
        self.assertNotIn("默认保留询问", INIT_REFERENCE)

    def test_init_step_order_permission_before_project_map(self) -> None:
        permission_step = INIT_REFERENCE.index("**权限**")
        self.assertLess(
            permission_step, INIT_REFERENCE.index("**生成或更新项目地图**")
        )
        self.assertLess(
            INIT_REFERENCE.index("**生成或更新项目地图**"),
            INIT_REFERENCE.index("**gitignore 校验**"),
        )
        self.assertLess(
            INIT_REFERENCE.index("**gitignore 校验**"),
            INIT_REFERENCE.index("**收尾**"),
        )

    def test_init_permission_step_is_completion_gate(self) -> None:
        gate = INIT_REFERENCE.index(shared.INIT_PERMISSION_GATE)
        self.assertLess(gate, INIT_REFERENCE.index("**生成或更新项目地图**"))
        self.assertLess(gate, INIT_REFERENCE.index("**gitignore 校验**"))
        self.assertLess(gate, INIT_REFERENCE.index("**收尾**"))

    def test_tdd_red_has_no_unverifiable_record_ritual(self) -> None:
        self.assertIn(shared.RED_CAUSE, SKILL)
        self.assertNotIn(shared.RED_RECORD, SKILL)

    def test_tdd_requires_self_explaining_code(self) -> None:
        self.assert_all(
            shared.SELF_EXPLAINING_CODE,
            shared.SELF_EXPLAINING_REFERENCE,
            "必须满足该标准",
        )
        for value in (
            shared.DOMAIN_NAMING,
            "输入、输出、副作用与失败方式",
            "代码表达“是什么”和“怎么做”",
            shared.COMMENTS_EXPLAIN_WHY,
            "独立函数",
            "高内聚",
        ):
            with self.subTest(value=value):
                self.assertIn(value, SELF_EXPLAINING_REFERENCE)
                self.assertNotIn(value, SKILL)

    def test_branch_policy_in_discipline_and_publish(self) -> None:
        discipline = SKILL.split("## 2. 通用纪律", 1)[1].split(
            "## 3. 分析", 1
        )[0]
        for value in (
            shared.BRANCH_PROTECTED_MAIN,
            shared.BRANCH_FEATURE_BRANCH,
            shared.BRANCH_NO_PERSISTENT_DEV,
            shared.BRANCH_COMMIT_ON_BRANCH,
            shared.BRANCH_USER_MERGE,
            shared.BRANCH_DELETE_AFTER_MERGE,
        ):
            with self.subTest(value=value):
                self.assertIn(value, discipline)
        self.assertNotIn("deploy/test", SKILL)
        self.assertNotIn("基于 dev 分支", SKILL)
        publish = SKILL.split("## 9. 全量测试与提交", 1)[1].split(
            "## 10. 重跑上限", 1
        )[0]
        self.assertIn("当前分支不是 main", publish)
        self.assertIn("停止并转人工", publish)
        self.assertNotIn("确认当前分支为 dev", publish)

    def test_init_commit_requires_non_main_branch(self) -> None:
        self.assertIn("非 main 分支", INIT_REFERENCE)
        self.assertIn("转人工", INIT_REFERENCE)
        self.assertNotIn("落在 dev 分支", INIT_REFERENCE)

    def test_branch_policy_old_markers_removed(self) -> None:
        for name in (
            "BRANCH_DEV_BASE",
            "BRANCH_DEPLOY_TEST",
            "BRANCH_SYNC_ALL",
            "BRANCH_COMMIT_ON_DEV",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(shared, name))

    def test_self_explaining_reference_has_exactly_four_pairs(self) -> None:
        self.assertTrue(SELF_EXPLAINING_PATH.is_file())
        self.assertEqual(
            SELF_EXPLAINING_REFERENCE.count(shared.BAD_EXAMPLE), 4
        )
        self.assertEqual(
            SELF_EXPLAINING_REFERENCE.count(shared.GOOD_EXAMPLE), 4
        )
        for topic in (
            "肯定式布尔命名",
            "魔法值与单位",
            "复杂控制流",
            "职责混杂的纯计算内联",
        ):
            with self.subTest(topic=topic):
                self.assertIn(topic, SELF_EXPLAINING_REFERENCE)
        self.assertNotIn(shared.BAD_EXAMPLE, SKILL)
        self.assertNotIn(shared.GOOD_EXAMPLE, SKILL)

    def test_positive_boolean_naming_standard_and_example(self) -> None:
        self.assertIn(shared.POSITIVE_BOOLEAN_NAMING,
                      SELF_EXPLAINING_REFERENCE)
        for value in ("`canEdit`", "`hasPermission`", "`isEditable`"):
            with self.subTest(value=value):
                self.assertIn(value, SELF_EXPLAINING_REFERENCE)
        self.assertIn("`!canEdit`", SELF_EXPLAINING_REFERENCE)
        self.assertIn("`canEdit` 表示当前主体的权限或能力",
                      SELF_EXPLAINING_REFERENCE)
        self.assertIn("`isEditable` 表示对象状态",
                      SELF_EXPLAINING_REFERENCE)
        self.assertIn("`isDeleted`、`isDisabled`", SELF_EXPLAINING_REFERENCE)

        example = SELF_EXPLAINING_REFERENCE.split("## 示例 1", 1)[1].split(
            "## 示例 2", 1
        )[0]
        bad = example.split(shared.BAD_EXAMPLE, 1)[1].split(
            shared.GOOD_EXAMPLE, 1
        )[0]
        good = example.split(shared.GOOD_EXAMPLE, 1)[1]
        self.assertIn(shared.NEGATIVE_BOOLEAN_BAD, bad)
        self.assertIn(shared.POSITIVE_BOOLEAN_GOOD, good)
        self.assertIn(shared.BOOLEAN_BEHAVIOR_BAD, bad)
        self.assertIn(shared.BOOLEAN_BEHAVIOR_GOOD, good)
        self.assertIn("心智反转", example)
        self.assertNotIn("isCannotEdit", good)

    def test_pure_function_extraction_standard_and_example(self) -> None:
        for value in (
            "纯计算逻辑应提取为具名独立函数",
            "高内聚、低耦合",
            "纯计算逻辑内联在读写、持久化等副作用流程中",
        ):
            with self.subTest(value=value):
                self.assertIn(value, SELF_EXPLAINING_REFERENCE)
        example = SELF_EXPLAINING_REFERENCE.split("## 示例 4", 1)[1].split(
            "## 审查结论", 1
        )[0]
        bad = example.split(shared.BAD_EXAMPLE, 1)[1].split(
            shared.GOOD_EXAMPLE, 1
        )[0]
        good = example.split(shared.GOOD_EXAMPLE, 1)[1]
        for part in (bad, good):
            for value in ("1000", "0.85"):
                with self.subTest(part=part, value=value):
                    self.assertIn(value, part)
        for value in (
            "apply_large_order_discount",
            "LARGE_ORDER_THRESHOLD",
            "LARGE_ORDER_DISCOUNT_RATE",
        ):
            with self.subTest(value=value):
                self.assertIn(value, good)
        self.assertNotIn("apply_large_order_discount", bad)

    def test_self_explaining_standard_has_context_exemptions(self) -> None:
        for value in (
            "生成代码与第三方代码",
            "框架、协议或公共 API",
            "短小且作用域明显",
            "只审查本次变更中的人工编写代码",
            "包内可定位的来源标记或契约证据",
            "包内可定位的外部契约证据",
            "`i`、`x`、`y`、`e`、`err`",
        ):
            with self.subTest(value=value):
                self.assertIn(value, SELF_EXPLAINING_REFERENCE)

    def test_gate_documented_before_tdd(self) -> None:
        for value in (
            "准入闸门",
            shared.SCRIPT_CHECK_ENV,
            shared.SCRIPT_VALIDATE_AC,
            "${SKILL_ROOT}/scripts/check-env.sh",
            "${SKILL_ROOT}/scripts/validate-ac.sh",
        ):
            with self.subTest(value=value):
                self.assertIn(value, SKILL)
        tdd_section = SKILL.index("## 5. TDD 实现与自测")
        self.assertLess(SKILL.index(shared.SCRIPT_CHECK_ENV), tdd_section)
        self.assertLess(SKILL.index(shared.SCRIPT_VALIDATE_AC), tdd_section)

    def test_environment_invariants_terminate_no_self_heal(self) -> None:
        for value in ("环境不变式", "终止", "不自愈"):
            with self.subTest(value=value):
                self.assertIn(value, SKILL)

    def test_final_section_reframes_branch_check_as_defensive(self) -> None:
        section = SKILL.split("## 9. 全量测试与提交", 1)[1].split(
            "## 10. 重跑上限", 1
        )[0]
        self.assertIn("防御性", section)
        self.assertIn("当前分支不是 main", section)
        self.assertIn("停止并转人工", section)

    def test_agent_file_mentions_gate_and_all_scripts(self) -> None:
        self.assertIn("准入闸门", AGENT)
        for value in (
            "${SKILL_ROOT}/scripts/check-scope.sh",
            "${SKILL_ROOT}/scripts/run-full-tests.sh",
            "${SKILL_ROOT}/scripts/check-env.sh",
            "${SKILL_ROOT}/scripts/validate-ac.sh",
            "${SKILL_ROOT}/scripts/parse-verdict.sh",
        ):
            with self.subTest(value=value):
                self.assertIn(value, AGENT)


if __name__ == "__main__":
    unittest.main()
