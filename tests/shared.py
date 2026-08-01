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

# Installer targets and legacy removal.
PLATFORMS = (".claude", ".claudeD", ".claudeP")
AGENT_NAMES = SKILL_NAMES
LEGACY_SKILLS = ("plan-dev-tasks", "dev-with-tdd")
