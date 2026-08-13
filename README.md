# agent-dev-workflow

一套面向 Claude Code、支持 Hermes profile 的单 feature 开发任务协作 skill bundle，由两个必须成对安装的 skill 组成：

- `plan-tdd-tasks` —— 唯一面向用户的开发入口与全流程主 agent：分析 → 规划（AC 清单 + 范围声明）→ TDD 实现与自测 → 机械范围检查 → 产出包 → 并行盲测 ×2 → 分歧处理 → 全量测试 → 提交。
- `blind-review-tasks` —— 纯只读、无执行环境的静态盲审复核者：只依据 AC 清单、代码包、测试与范围声明做独立 code review，输出结构化 verdict。只由 `plan-tdd-tasks` 并行派发。

哲学：**机械的脚本化，判断的留给人，盲测防自证，契约测试锁死**。与旧版（`plan-dev-tasks` / `dev-with-tdd`）的关系：旧架构（状态机、版本号、gates、协调器、hooks 强制层）已整体退役并删除；本仓库从零重建。

## 工作流

```text
① 主 agent 分析 → ② 规划（AC 清单 + 范围声明 + test-command.txt，规划不落盘）
→ ③ TDD 实现与自测 → ④ 先运行机械范围检查 → ⑤ 产出包
→ ⑥ 盲测 ×2（并行、只读、全新上下文，输入只有 AC/代码/测试/范围声明）
→ ⑦ 分歧处理（双 pass 继续 / 双 fail 只给证据重修 / 相左自辩后人工仲裁）
→ ⑧ run-full-tests.sh 全量测试（每次尝试最后、恰好 1 遍）
→ ⑨ 最终范围复检 + git add 范围内文件 + 一次 commit → 清理 → 汇报
```

重跑上限：盲测最多 2 轮，超限强制人工。

### 分支策略

main/master 是保护分支，不直接提交。所有开发基于 dev 分支：发版完成后基于最新 main checkout dev；dev 开发完成后 merge 到 deploy/test 发布测试环境；迭代完成后将 dev merge/MR 回 main，保持 main/master/dev/deploy/* 同步。任务的最终提交必须落在 dev（不在 dev 时先与用户确认再切换）。

### 分歧处理

| A \ B | pass | fail |
|---|---|---|
| pass | 全量测试 | 自辩 |
| fail | 自辩 | 双 fail：只读证据、禁反驳、修复后重派 |

相左时主 agent 写 `review/rebuttal.md`（接受+修复方案 或 反驳+包内证据）呈交用户仲裁，以用户裁决为准。

### 自解释代码标准

实现代码必须让任何人或 AI 从命名、类型和结构直接理解领域含义、输入输出、副作用与失败方式。存在等价的肯定谓词时，布尔变量和谓词必须使用肯定语义，例如使用 `canEdit` 而不是 `isCannotEdit`。代码表达“是什么”和“怎么做”；注释只解释代码无法表达的“为什么”，不得承担翻译代码的职责。

统一标准位于 `skills/plan-tdd-tasks/references/self-explaining-code.md`，包含 4 组 Bad/Good 对照，覆盖含义不明的命名、魔法值与单位、依赖注释的复杂控制流、职责混杂的纯计算内联。标准只审查本次变更中的人工编写代码，并为生成/第三方代码、外部契约名称和短小局部约定名定义需要包内可定位来源或契约证据的边界。主 skill 实现前读取它；盲审 skill 通过“检查 4：自解释性”按同一标准复核，避免实现者自证。

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

`files:` + `infra:` 是机械检查的声明集；`约束:` 仅咨询性。范围检查先于产出包：**偶发且非必要的越界**只清理越界内容并按原 scope 重试；**实现确实需要扩大范围**才先回退越界改动，再重新规划与实现。两种情况都禁止事后修补 scope.md 追认改动。

全量测试失败也按盲审事实分流：**代码、测试、AC 或 scope 发生变化**时重新检查、产包并盲审；**只有环境或测试命令变化且代码包未变**时保留上一轮双 PASS，直接重试全量测试。环境或测试命令修复最多重试 2 次，连续失败后转人工。

全量通过后，若需要则先更新 project-map，再**再次运行 §6 的 check-scope.sh**；只有最终范围复检通过，才暂存范围内文件并一次提交。

### 包布局

```text
.tmp/<task-id>/
├── package/  ac-list.md, scope.md, test-command.txt, diff.txt, code/
├── review/   A.md, B.md, rebuttal.md（仅分歧时）
└── full-tests.log
```

### project-map.md（项目地图：项目的索引）

`PROJECT_ROOT/project-map.md` 是本 bundle 唯一要求主 agent 在业务仓库维护的持久化项目元数据：作为项目的索引，让后续 agent 快速熟悉项目、确认变更文件。内容参考类别（按项目形态取舍）：架构、选型、前端路由、后端 API、公共组件、API auth；只写入方便其他 agent 使用的有价值内容。读取时机是普通任务分析期；普通任务发现地图缺失时**只提示运行 `/plan-tdd-tasks init`**，不创建地图。创建时机与全局漂移判定只在 init；普通任务**不执行全局漂移判定**，更新时机仅限本次 feature 改变地图已记录主题，此时更新对应小节并列入 `infra:`。init 细节由 `skills/plan-tdd-tasks/references/init.md` 负责。它是项目元数据而非规划产物——设计意图仍只存在于对话。盲测者不读取 project-map.md。

## 脚本接口

脚本随 `plan-tdd-tasks` skill 分发（`${SKILL_ROOT}/scripts/`），以绝对路径调用，均有契约测试。

### `check-scope.sh`

```text
check-scope.sh --project-root <dir> --scope-file <path> [--base <rev>]
```

changed = 工作树 diff vs base ∪ 未跟踪文件，减掉 `.tmp/` 下所有路径（无条件排除）。脚本使用 Git NUL 分隔路径，Unicode、空格、制表符等文件名按原始字节精确匹配；因此该脚本要求 bash。越界文件逐行输出 `out-of-scope <path>`，末行状态：

| 退出码 | 状态行 |
|---|---|
| 0 | `scope-check: PASS (n changed, m declared)` |
| 1 | `scope-check: FAIL (n out-of-scope files)` |
| 2 | 用法/校验错误（stderr 报错） |

### `run-full-tests.sh`

```text
run-full-tests.sh --project-root <dir> --test-cmd <string> [--workdir <dir>] [--log-file <path>]
```

`--test-cmd` 经 `sh -c` 执行（"全量"由主 agent 分析期确定并写入 `test-command.txt`，规则：必须覆盖仓库完整测试套件，禁止只跑新增测试）。相对 `--log-file` 始终以 `--project-root` 为基准解析，不受 `--workdir` 影响。输出与日志一致，末行状态：

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

安装器**自动移除旧版遗留**（`skills/plan-dev-tasks`、`skills/dev-with-tdd` 及其 agent 文件），不触碰其他任何 skill、agent 或配置。所有校验（HOME、源文件、平台容器）在首次删除前完成；容器若是普通文件而非目录则 fail closed。未知参数报错。

`install.sh -p <profile>`（**互斥**模式，与 Claude 平台安装二选一）安装到 Hermes 命名 profile（`~/.hermes/profiles/<profile>/`）：只分发两个 skill（Hermes 无 .md agent 机制，子代理经 `delegate_task` 运行时定义），不触碰 Claude 平台；profile 目录不存在时输出 `skip`，不会代为创建。主 skill 按宿主选择 Claude Code `Agent(blind-review-tasks)` 或 Hermes `delegate_task`；宿主传输不可用、无法创建两个全新上下文或无法认证结果来源时 fail closed，即停止流程。

**卸载**：手动删除两个 skill 目录与两个 agent 文件：

```text
~/.claude/skills/plan-tdd-tasks
~/.claude/skills/blind-review-tasks
~/.claude/agents/plan-tdd-tasks.md
~/.claude/agents/blind-review-tasks.md
```

（其他平台根同理）。Claude Code 安装新增 definitions 后需启动新会话或重启现有会话才会出现在 `/agents`。

## 首次使用：初始化（`/plan-tdd-tasks init`）

在业务仓库首次使用前，可运行 `/plan-tdd-tasks init` 做一次性初始化（**仅字面触发**；自然语言请求一律走正常任务流程）：

1. 生成 `project-map.md`（若不存在，按 `plan-tdd-tasks` skill §11.3 判定项目形态、自判类别）；已存在时做**漂移判定**（核对机械可验证的现状事实，不做风格性改写），无漂移则报告无需更新，有漂移**经用户同意后更新**；
2. 经用户同意后，通过 `update-config` skill 在 `.claude/settings.local.json` 添加 `` `Read(<PROJECT_ROOT>/**)` `` 读权限（拒绝则跳过）；`update-config` 是可选宿主能力，本 bundle 无硬运行时依赖，skill 不可用时报告 `update-config unavailable; permission step skipped` 并继续其余步骤；
3. 仅当 `.claude/settings.local.json` 已存在或本次写入时，机械校验它已被 gitignore；未忽略时追加到仓库 `.gitignore`，防止后续任务的范围检查误判；
4. 展示将提交内容后一次 commit 收尾（地图生成为 `chore: init project-map`，地图更新为 `chore: update project-map`），工作树保持 clean。

init 不是任务，仅做初始化：无 AC 清单、无范围声明、无盲测、无 TDD，不写入 `.tmp/`；入口规则见 `plan-tdd-tasks` skill §12，详细步骤见 `skills/plan-tdd-tasks/references/init.md`。

## 验证

仓库自测：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s skills/plan-tdd-tasks/tests -p 'test_*.py'
python3 -m unittest discover -s skills/blind-review-tasks/tests -p 'test_*.py'
bash -n install.sh
bash -n skills/plan-tdd-tasks/scripts/check-scope.sh
sh -n skills/plan-tdd-tasks/scripts/run-full-tests.sh
git diff --check
```

端到端冒烟：在 scratch 仓库用一个玩具 feature 走完整流程——两个并行盲测子代理、verdict 落盘、盲测者只读（transcript 无写工具调用）、check-scope 抓越界编辑、全量经脚本跑 1 遍、仅最后 commit。可选：在本地 `settings.json` 预放行盲测者读包路径（如 `Read(//Users/<you>/**)`）以减少权限弹窗。

## 已知限制

- 脚本仅支持 macOS/Linux（bash/sh）。
- 静态盲测无法捕获运行时错误——由最终全量测试兜底；盲测者之间可能相关性偏盲——由分歧自辩、人工仲裁与 2 轮上限兜底。
- 盲测者只读由 agent 定义的 `tools: Read, Grep, Glob` 在 harness 层强制；旧版 hooks 强制层不在本设计内（如需可作未来可选加固）。
- Hermes 平台：`install.sh -p <profile>` 互斥安装到命名 profile；主 skill 并行使用两个 `delegate_task` child，子代理继承父代理 toolsets（无只读参数），盲测者只读为**指令约束而非 harness 强制**，留待 VPS 实测。
