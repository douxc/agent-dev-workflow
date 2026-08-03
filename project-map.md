# project-map

## 架构

- 本仓库是 Claude Code 的 skill bundle 源码仓库（canonical 来源），非业务应用；安装与验证见 README「安装」「验证」节。
- 两个成对安装的 skill：`skills/plan-tdd-tasks/`（单 feature 开发全流程主 skill：分析 → 规划（AC 清单 + 范围声明 + test-command.txt）→ TDD → 产出包 + 机械范围检查 → 并行盲测 ×2 → 分歧处理 → 全量测试 → 提交）与 `skills/blind-review-tasks/`（纯只读静态盲审复核者，只由主 skill 并行派发）。
- 主 skill 随包分发两个脚本：`skills/plan-tdd-tasks/scripts/check-scope.sh`（机械范围检查）与 `run-full-tests.sh`（全量测试），以绝对路径调用，均有契约测试。
- agent definitions 在 `adapters/claude-code/agents/`（plan-tdd-tasks.md / blind-review-tasks.md）；`install.sh` 把 skills + agents 复制到每个已存在的平台根（~/.claude、~/.claudeD、~/.claudeP），自动移除旧版遗留（plan-dev-tasks / dev-with-tdd），不碰任何配置。
- 主 skill 支持字面 `/plan-tdd-tasks init` 进入 init 模式（SKILL.md §12）：生成 project-map.md、配置项目读权限、一次 chore commit 收尾。
- 业务仓库侧的唯一持久化项目元数据是 `PROJECT_ROOT/project-map.md`；任务产物在 `.tmp/<task-id>/`（package/ review/ full-tests.log）。

## 选型

- bash/sh（install.sh 与两个脚本）；Python 3 标准库 unittest（契约测试）；无运行时依赖。
- 哲学：机械的脚本化，判断的留给人，盲测防自证，契约测试锁死；无状态机、无版本号、无 gates。

## 测试

- 仓库自测（README「验证」节）：`python3 -m unittest discover -s tests -p 'test_*.py'`（脚本行为 / 文档 / 安装 / agent 契约）、`skills/plan-tdd-tasks/tests`（主 skill 契约）、`skills/blind-review-tasks/tests`（盲审契约）；`bash -n install.sh`；`sh -n` 两个脚本；`git diff --check`。
- 契约测试以 `tests/shared.py` 为单一事实来源（标记常量），文档或脚本与契约漂移即红。
