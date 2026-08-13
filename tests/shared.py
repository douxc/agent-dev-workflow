"""CLI and format contract constants — single source of truth.

Imported by both the script behavior tests and the skill contract tests so
the two cannot drift: renaming a flag or changing an exit code breaks both.
"""

# Script names and locations (shipped inside the main skill so the installer
# distributes them with the skill).
SKILL_NAMES = ("plan-tdd-tasks", "blind-review-tasks")
MAIN_SKILL = "plan-tdd-tasks"
REVIEW_SKILL = "blind-review-tasks"
SCRIPT_CHECK_SCOPE = "check-scope.sh"
SCRIPT_RUN_FULL_TESTS = "run-full-tests.sh"

# Flags.
FLAG_PROJECT_ROOT = "--project-root"
FLAG_SCOPE_FILE = "--scope-file"
FLAG_BASE = "--base"
FLAG_TEST_CMD = "--test-cmd"
FLAG_WORKDIR = "--workdir"
FLAG_LOG_FILE = "--log-file"
FLAG_PROFILE = "-p"

# Exit codes.
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

# check-scope.sh status lines and markers.
SCOPE_CHECK_PASS = "scope-check: PASS"
SCOPE_CHECK_FAIL = "scope-check: FAIL"
OUT_OF_SCOPE = "out-of-scope"
UNCHANGED = "unchanged"
STAGED_WARNING = "staged:"

# run-full-tests.sh status lines.
RUN_FULL_TESTS_PASS = "run-full-tests: PASS"
RUN_FULL_TESTS_FAIL = "run-full-tests: FAIL"
RUN_FULL_TESTS_USAGE = "run-full-tests: USAGE ERROR"

# 范围声明 markers.
SCOPE_MARKER_FILES = "files:"
SCOPE_MARKER_INFRA = "infra:"

# AC 清单 grammar markers and values.
AC_HEADER = "## AC 清单"
AC_ITEM = "- AC-"
AC_ASSERT = "- 断言:"
AC_OWNER = "- 归属:"
AC_VERIFY = "- 验证:"
AC_VERIFY_VALUES = ("unit", "integration", "scripted")
AC_BANNED_WORDS = ("合理", "适当", "优雅", "快速", "尽可能", "一些")

# verdict block markers.
VERDICT_PASS = "verdict: PASS"
VERDICT_FAIL = "verdict: FAIL"
VERDICT_ITEM = "[AC-"
VERDICT_EVIDENCE = "证据:"
VERDICT_REASON = "理由:"

# Package layout.
PACKAGE_FILES = (
    "ac-list.md",
    "scope.md",
    "test-command.txt",
    "diff.txt",
    "code",
)
TMP_ROOT = ".tmp"
REVIEW_DIR = "review"

# project-map.md (项目地图) markers — reference category list, chosen by the
# main agent per project shape (frontend/backend split vs monolith).
PROJECT_MAP = "project-map.md"
PM_SECTIONS = ("架构", "选型", "前端路由", "后端 API", "公共组件", "API auth")

# init 模式 markers — literal `/plan-tdd-tasks init` is the only init trigger;
# the permission rule and the closing chore commit are init's distinguishing
# behaviors. Full strings only, never the bare word "init" (substring hazard).
INIT_TRIGGER = "/plan-tdd-tasks init"
INIT_NOT_A_TASK = "init 不是任务"
INIT_PERMISSION = "Read(<PROJECT_ROOT>/**)"
INIT_COMMIT = "chore: init project-map"
INIT_EXCEPTION = "§12 init 收尾提交"

# init 漂移判定 markers — an existing project-map.md is drift-checked instead
# of skipped-and-reported; consent gates the update; the update uses a distinct
# closing commit message. One constant per behavior phrase asserted in the
# contract tests, so every AC-asserted string is anchored in a test.
INIT_DRIFT_CHECK = "漂移判定"
INIT_DRIFT_UPDATE_CONSENT = "经用户同意后更新"
INIT_DRIFT_REFUSE_SKIP = "拒绝则跳过并报告"
INIT_DRIFT_MECHANICAL = "机械可验证"
INIT_DRIFT_NO_STYLE = "风格性改写"
INIT_DRIFT_NO_UPDATE = "无需更新"
INIT_DRIFT_TABLE_ROW = "更新时机（init）"
INIT_UPDATE_COMMIT = "chore: update project-map"

# init 权限模板 markers — init 写入的权限规则不是单条 Read，而是一份模板
# （references/permission-template.md），init 将 <PROJECT_ROOT> 替换为实际项目根。
# 通用基线与按语言取舍写入 permissions.allow；ask：变更类默认保留询问。
INIT_PERMISSION_TEMPLATE = "references/permission-template.md"
INIT_PERMISSION_BASELINE = "通用基线"
INIT_PERMISSION_PER_LANGUAGE = "按语言取舍"
INIT_PERMISSION_ASK_GROUP = "ask：变更类"
INIT_PERMISSION_KEEP_ASK = "默认保留询问"

# Installer targets and legacy removal.
PLATFORMS = (".claude", ".claudeD", ".claudeP")
AGENT_NAMES = SKILL_NAMES
LEGACY_SKILLS = ("plan-dev-tasks", "dev-with-tdd")

# Hermes profile install markers — `install.sh -p <profile>` is mutually
# exclusive with Claude platform install; named profiles live under
# ~/.hermes/profiles/; Hermes has no .md agent mechanism so only skills ship.
HERMES_PROFILES_DIR = ".hermes/profiles"
INSTALL_PROFILE_EXCLUSIVE = "互斥"
HERMES_BLIND_READONLY = "指令约束而非 harness 强制"
HERMES_DELEGATE_TASK = "delegate_task"
TRANSPORT_UNAVAILABLE = "宿主传输不可用"
TRANSPORT_FAIL_CLOSED = "fail closed"
TRANSPORT_STOP = "停止流程"
TRANSPORT_FAIL_CLOSED_RULE = (
    "宿主传输不可用、无法创建两个全新上下文或无法认证结果来源时 "
    "**fail closed**：停止流程"
)
UPDATE_CONFIG_UNAVAILABLE = (
    "update-config unavailable; permission step skipped"
)

# Workflow de-duplication markers.
SCOPE_BEFORE_PACKAGE = "先运行机械范围检查"
PACKAGE_BUILD = "生成 `diff.txt`"
SCOPE_ACCIDENTAL = "偶发且非必要的越界"
SCOPE_EXPANSION = "实现确实需要扩大范围"
FULL_FAIL_PACKAGE_CHANGE = "代码、测试、AC 或 scope 发生变化"
FULL_FAIL_NO_PACKAGE_CHANGE = "只有环境或测试命令变化且代码包未变"
PROJECT_MAP_INIT_HINT = "只提示运行 `/plan-tdd-tasks init`"
PROJECT_MAP_NO_GLOBAL_DRIFT = "不执行全局漂移判定"
INIT_REFERENCE = "references/init.md"
RED_CAUSE = "确认失败原因是行为缺失"
RED_RECORD = "记录命令与失败原因"
FINAL_SCOPE_RECHECK = "再次运行 §6 的 check-scope.sh"
ENV_RETRY_CAP = "环境或测试命令修复最多重试 2 次"

# Self-explaining code standard markers.
SELF_EXPLAINING_CODE = "自解释代码"
SELF_EXPLAINING_REFERENCE = "references/self-explaining-code.md"
DOMAIN_NAMING = "标识符必须表达领域含义"
COMMENTS_EXPLAIN_WHY = "注释只解释代码无法表达的“为什么”"
CHECK_4_SELF_EXPLAINING = "检查 4：自解释性"
BAD_EXAMPLE = "### Bad"
GOOD_EXAMPLE = "### Good"
VERDICT_ANY_FAIL = "任一 FAIL 块存在时，末行必须是 `verdict: FAIL`"
VERDICT_ALL_PASS = "仅当所有必需块均为 PASS 时"
POSITIVE_BOOLEAN_NAMING = (
    "存在等价的肯定谓词时，布尔变量和谓词必须使用肯定语义"
)
NEGATIVE_BOOLEAN_BAD = 'const isCannotEdit = user.role !== "admin";'
POSITIVE_BOOLEAN_GOOD = 'const canEdit = user.role === "admin";'
BOOLEAN_BEHAVIOR_BAD = "setEditorVisibility(!isCannotEdit);"
BOOLEAN_BEHAVIOR_GOOD = "setEditorVisibility(canEdit);"

# Branch policy markers.
BRANCH_PROTECTED_MAIN = "main/master 是保护分支"
BRANCH_FEATURE_BRANCH = "基于最新 main checkout 一个临时分支"
BRANCH_NO_PERSISTENT_DEV = "无长期 dev 分支"
BRANCH_COMMIT_ON_BRANCH = "commit 到该临时分支"
BRANCH_USER_MERGE = "由用户主动触发"
BRANCH_DELETE_AFTER_MERGE = "merge 完成后删除"
