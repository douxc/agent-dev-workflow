# agent-dev-workflow

一套面向 Claude Code 的单 feature 开发任务协作 skill bundle，由两个必须成对安装的 skill 组成：

- `plan-tdd-tasks` —— 唯一面向用户的开发入口与全流程主 agent：分析 → 规划（AC 清单 + 范围声明）→ TDD 实现与自测 → 产出包 → 机械范围检查 → 并行盲测 ×2 → 分歧处理 → 全量测试 → 提交。
- `blind-review-tasks` —— 纯只读、无执行环境的静态盲审复核者：只依据 AC 清单、代码包、测试与范围声明做独立 code review，输出结构化 verdict。只由 `plan-tdd-tasks` 并行派发。

哲学：**机械的脚本化，判断的留给人，盲测防自证，契约测试锁死**。与旧版（`plan-dev-tasks` / `dev-with-tdd`）的关系：旧架构（状态机、版本号、gates、协调器、hooks 强制层）已整体退役并删除；本仓库从零重建。

## 工作流

```text
① 主 agent 分析 → ② 规划（AC 清单 + 范围声明 + test-command.txt，规划不落盘）
→ ③ TDD 实现与自测 → ④ 产出包 + check-scope.sh 机械范围检查
→ ⑤ 盲测 ×2（并行、只读、全新上下文，输入只有 AC/代码/测试/范围声明）
→ ⑥ 分歧处理（双 pass 继续 / 双 fail 只给证据重修 / 相左自辩后人工仲裁）
→ ⑦ run-full-tests.sh 全量测试（最后、恰好 1 遍）
→ ⑧ git add 范围内文件 + 一次 commit → 清理 → 汇报
```

重跑上限：盲测最多 2 轮，超限强制人工。

### 分歧处理

| A \ B | pass | fail |
|---|---|---|
| pass | 全量测试 | 自辩 |
| fail | 自辩 | 双 fail：只读证据、禁反驳、修复后重派 |

相左时主 agent 写 `review/rebuttal.md`（接受+修复方案 或 反驳+包内证据）呈交用户仲裁，以用户裁决为准。

## 产物格式

### AC 清单（`ac-list.md`）—— 承重墙

```text
## AC 清单

- AC-1: 新增 hello() 函数，输入任意字符串 name，返回 "hello, <name>"。
  - 断言: hello("world") 的返回值等于 "hello, world"（精确字符串，大小写敏感）
  - 归属: src/greeter.py
  - 验证: unit
```

- 一个 AC 一个行为，禁止复合 AC（"并"）。
- 断言必须命名真实标识符 + 精确期望值；禁止主观词：合理、适当、优雅、快速、尽可能、一些。
- 归属（逗号分隔）必须是范围声明 `files:` 的条目；反向：每个 `files:` 文件必须被 ≥1 条 AC 归属覆盖或列入 `infra:`。
- 验证三选一：`unit | integration | scripted`，标签必须诚实。

### 范围声明（`scope.md`）—— 实现前写定，事后禁止修补

```text
## 范围声明
task: <task-id>
base: <HEAD sha>
files:
- src/greeter.py
- src/cli.py
- tests/test_greeter.py
infra:
- pyproject.toml
约束:
- 不修改 src/legacy/* 下任何文件
```

`files:` + `infra:` 是机械检查的声明集；`约束:` 仅咨询性。越界时流程要求**先回退越界改动 → 重新规划 → 重新实现**，禁止事后修补 scope.md。

### 包布局

```text
.tmp/<task-id>/
├── package/  ac-list.md, scope.md, test-command.txt, diff.txt, code/
├── review/   A.md, B.md, rebuttal.md（仅分歧时）
└── full-tests.log
```

### project-map.md（项目地图：项目的索引）

`PROJECT_ROOT/project-map.md` 是本 bundle 唯一要求主 agent 在业务仓库维护的持久化项目元数据：作为项目的索引，让后续 agent 快速熟悉项目、确认变更文件。内容参考类别（按项目形态取舍）：架构、选型、前端路由、后端 API、公共组件、API auth；只写入方便其他 agent 使用的有价值内容。读取时机、创建时机、更新时机见 `plan-tdd-tasks` skill §11；创建或更新的任务必须将其列入范围声明 `infra:`。它是项目元数据而非规划产物——设计意图仍只存在于对话。盲测者不读取 project-map.md。

## 脚本接口

脚本随 `plan-tdd-tasks` skill 分发（`${SKILL_ROOT}/scripts/`），以绝对路径调用，均有契约测试。

### `check-scope.sh`

```text
check-scope.sh --project-root <dir> --scope-file <path> [--base <rev>]
```

changed = 工作树 diff vs base ∪ 未跟踪文件，减掉 `.tmp/` 下所有路径（无条件排除）。越界文件逐行输出 `out-of-scope <path>`，末行状态：

| 退出码 | 状态行 |
|---|---|
| 0 | `scope-check: PASS (n changed, m declared)` |
| 1 | `scope-check: FAIL (n out-of-scope files)` |
| 2 | 用法/校验错误（stderr 报错） |

### `run-full-tests.sh`

```text
run-full-tests.sh --project-root <dir> --test-cmd <string> [--workdir <dir>] [--log-file <path>]
```

`--test-cmd` 经 `sh -c` 执行（"全量"由主 agent 分析期确定并写入 `test-command.txt`，规则：必须覆盖仓库完整测试套件，禁止只跑新增测试）。输出与日志一致，末行状态：

| 退出码 | 状态行 |
|---|---|
| 0 | `run-full-tests: PASS` |
| 1 | `run-full-tests: FAIL (exit N)` |
| 2 | `run-full-tests: USAGE ERROR` |

## 安装

```bash
git clone https://github.com/douxc/agent-dev-workflow.git
cd agent-dev-workflow
./install.sh
```

安装器把两个 skill 与两个 agent definitions 直接复制到每个**已存在**的平台根目录（`~/.claude`、`~/.claudeD`、`~/.claudeP`）的 `skills/` 与 `agents/` 下；平台根目录不存在时输出 `skip`，不会代为创建。源仓库是唯一 canonical 来源：不保留单独的 canonical 副本，不创建任何软链接；每次运行先删除旧目标再全新复制，可重复执行，不产生 `.backup.*`。

安装器**自动移除旧版遗留**（`skills/plan-dev-tasks`、`skills/dev-with-tdd` 及其 agent 文件），不触碰其他任何 skill、agent 或配置。所有校验（HOME、源文件、平台容器）在首次删除前完成；容器若是普通文件而非目录则 fail closed。安装器不接受任何参数（未知参数报错）。

**卸载**：手动删除两个 skill 目录与两个 agent 文件：

```text
~/.claude/skills/plan-tdd-tasks
~/.claude/skills/blind-review-tasks
~/.claude/agents/plan-tdd-tasks.md
~/.claude/agents/blind-review-tasks.md
```

（其他平台根同理）。Claude Code 安装新增 definitions 后需启动新会话或重启现有会话才会出现在 `/agents`。

## 验证

仓库自测：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s skills/plan-tdd-tasks/tests -p 'test_*.py'
python3 -m unittest discover -s skills/blind-review-tasks/tests -p 'test_*.py'
bash -n install.sh
sh -n skills/plan-tdd-tasks/scripts/check-scope.sh
sh -n skills/plan-tdd-tasks/scripts/run-full-tests.sh
git diff --check
```

端到端冒烟：在 scratch 仓库用一个玩具 feature 走完整流程——两个并行盲测子代理、verdict 落盘、盲测者只读（transcript 无写工具调用）、check-scope 抓越界编辑、全量经脚本跑 1 遍、仅最后 commit。可选：在本地 `settings.json` 预放行盲测者读包路径（如 `Read(//Users/<you>/**)`）以减少权限弹窗。

## 已知限制

- 脚本仅支持 macOS/Linux（bash/sh）。
- 静态盲测无法捕获运行时错误——由最终全量测试兜底；盲测者之间可能相关性偏盲——由分歧自辩、人工仲裁与 2 轮上限兜底。
- 盲测者只读由 agent 定义的 `tools: Read, Grep, Glob` 在 harness 层强制；旧版 hooks 强制层不在本设计内（如需可作未来可选加固）。
- Hermes 平台适配后置。
