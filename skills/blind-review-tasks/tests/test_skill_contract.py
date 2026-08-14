from pathlib import Path
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))
import shared


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")


class BlindReviewTasksContractTest(unittest.TestCase):
    def assert_all(self, *values: str) -> None:
        for value in values:
            with self.subTest(value=value):
                self.assertIn(value, SKILL)

    def test_read_only_discipline(self) -> None:
        self.assert_all(
            "Read, Grep, Glob",
            "没有执行环境",
            "不得声称运行过任何测试或代码",
            "工具缺失是预期而非故障",
        )

    def test_input_boundary(self) -> None:
        self.assert_all(
            "ac-list.md",
            "scope.md",
            "diff.txt",
            "code/",
            "不得读取 package 目录之外的 `.tmp` 内容",
            "verdict 每条证据必须指向包内路径",
        )

    def test_no_test_run_evidence_in_blind_review(self) -> None:
        # Lock-in assertion: the blind reviewer is pure static — no run log
        # input and no citable run conclusion. Guards against reintroducing
        # the retired blind-phase test execution.
        self.assertNotIn("test-run.log", SKILL)
        self.assertNotIn("运行证据", SKILL)
        self.assertNotIn("可选运行证据", SKILL)

    def test_check_1_ac_completeness(self) -> None:
        self.assert_all(
            "AC 完整性映射",
            "实现存在",
            "断言可机械验证",
            "测试覆盖该断言",
        )

    def test_check_2_test_coverage(self) -> None:
        self.assert_all(
            "测试覆盖变更代码",
            "断言锚点",
            "被测试断言触及",
        )

    def test_check_3_test_boundaries(self) -> None:
        self.assert_all(
            "测试边界合理",
            "同义反复测试",
            "孤岛测试",
            "mock 不掩盖真实行为",
            "断言粒度不塌缩",
        )

    def test_check_4_self_explaining_code(self) -> None:
        self.assert_all(
            shared.CHECK_4_SELF_EXPLAINING,
            f"../plan-tdd-tasks/{shared.SELF_EXPLAINING_REFERENCE}",
            "4 组 Bad/Good 样例",
            "`适用边界`",
            "`审查结论`",
            "只审查本次变更中的人工编写代码",
            "[检查4] PASS",
            "[检查4-n]",
        )
        section = SKILL.split(f"## 6. {shared.CHECK_4_SELF_EXPLAINING}", 1)[
            1
        ].split("## 7. verdict 输出格式", 1)[0]
        for duplicated_rule in (
            "- 命名是否",
            "- 函数的输入",
            "- 数字、字符串和单位",
            "- 控制流是否",
            "- 注释是否",
        ):
            with self.subTest(duplicated_rule=duplicated_rule):
                self.assertNotIn(duplicated_rule, section)

    def test_verdict_format(self) -> None:
        self.assert_all(
            shared.VERDICT_PASS,
            shared.VERDICT_FAIL,
            shared.VERDICT_ITEM,
            shared.VERDICT_EVIDENCE,
            shared.VERDICT_REASON,
            "禁止任何散文段落",
            "修复建议",
            "末行必须为",
        )

    def test_verdict_aggregate_matches_blocks(self) -> None:
        self.assert_all(shared.VERDICT_ANY_FAIL, shared.VERDICT_ALL_PASS)

    def test_evidence_requires_file_line(self) -> None:
        self.assert_all("包内路径 + 行号", "没有行号不可称证据")

    def test_blindness_boundary_project_map(self) -> None:
        # Lock-in assertion: the blind reviewer must never learn about the
        # project map (it carries implementation-side context). Intentionally
        # green by construction — guards against future accidental mention.
        self.assertNotIn(shared.PROJECT_MAP, SKILL)


if __name__ == "__main__":
    unittest.main()
