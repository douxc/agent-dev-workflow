# agent-dev-workflow

一套面向 Claude Code、支持 Hermes profile 的单 feature 开发任务协作 skill bundle，由两个必须成对安装的 skill 组成：

- `plan-tdd-tasks` —— 唯一面向用户的开发入口与全流程主 agent：分析 → 规划（AC 清单 + 范围声明）→ 准入闸门 → TDD 实现与自测 → 机械范围检查 → 全量测试 → 产出包 → 并行盲测 ×2 → 分歧处理 → 提交。
- `blind-review-tasks` —— 纯只读、无执行环境的静态盲审复核者：只依据 AC 清单、代码包、测试与范围声明做独立 code review，输出结构化 verdict。只由 `plan-tdd-tasks` 并行派发。

哲学：**机械的脚本化，判断的留给人，盲测防自证，契约测试锁死**。与旧版（`plan-dev-tasks` / `dev-with-tdd`）的关系：旧架构（状态机、版本号、gates、协调器、hooks 强制层）已整体退役并删除；本仓库从零重建。

## 工作流

```text
① 主 agent 分析 → ② 规划（AC 清单 + 范围声明 + test-command.txt，规划不落盘）
→ ③ 准入闸门（check-env.sh 环境不变式 + validate-ac.sh AC 校验）
→ ④ TDD 实现与自测 → ⑤ 先运行机械范围检查 → ⑥ 全量测试（恰好 1 遍）+ 产出包
→ ⑦ 盲测阶段（盲测 ×2，并行、只读、全新上下文，输入只有 AC/代码/测试/范围声明）
→ ⑧ 分歧处理（双 pass 继续 / 双 fail 只给证据重修 / 相左自辩后人工仲裁）
→ ⑨ stage-scope.sh 提交（最终范围复检 + 一次 commit）
→ ⑩ 清理 → 汇报
```

重跑上限：盲测最多 2 轮，超限强制人工。

盲测阶段是纯静态只读复核，不执行任何测试。全量测试在 TDD 完成后、提交盲测前运行恰好 1 遍（§6）：全量不通过说明本次修改影响了其他模块（需修复），或前期范围规划有未覆盖（需回退重规划），必须在盲测前解决。分析期推断不出测试命令（不存在 package.json 且无测试套件、执行环境或测试脚本）时**主动询问用户是否跳过测试执行**：同意则 `test-command.txt` 写入字面 `SKIP`，§6 不运行全量测试、提交门禁以用户显式同意替代，汇报声明"测试未执行"；不同意则用户提供命令或修复环境后继续。§9 不再执行测试，只做提交收尾。

### 快速导航与限时分析

普通任务先从需求提取 1–3 个领域关键词，只搜索一次 `project-map.md`，目标 10–20 秒内返回领域、生产者、消费者与路径，并标记为“待源码验证的导航候选”；索引阶段不展开源码。地图未命中则立即进入常规源码分析。

源码分析从候选入口开始验证。约 5 分钟仍未收敛时暂停，汇报已确认、已排除、未确认与残余风险，由用户选择继续探索或接受当前范围。继续探索会追加一个 5 分钟窗口并在结束后再次询问；接受时仅以已确认内容生成 AC 和 scope，未确认项只保留为对话中的风险说明。时间均为软预算，工具调用跨过预算时在返回后进入检查点。

### 分支策略

main/master 是保护分支，不直接提交。开发基于最新 main checkout 一个临时分支（无长期 dev 分支）；开发、修复、调整完成后 commit 到该临时分支。由用户主动触发 merge 到 main；merge 完成后删除本地临时分支，main 始终保持最新且工作树 clean。任务的最终提交必须落在临时分支。

### 分歧处理

| A \ B | pass | fail |
|---|---|---|
| pass | 提交收尾（§9） | 自辩 |
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

全量测试（§6 提交盲测前，恰好 1 遍）失败按盲审事实分流：**代码、测试、AC 或 scope 发生变化**时修复后重新检查并重跑，再产包并盲审；**只有环境或测试命令变化且代码包未变**时修复后直接重试全量测试。环境或测试命令修复最多重试 2 次，连续失败后转人工。

全量通过后**再次运行 §6 的 check-scope.sh**；只有最终范围复检通过，才暂存范围内文件并一次提交。

### 包布局

```text
.tmp/<task-id>/
├── package/  ac-list.md, scope.md, test-command.txt, diff.txt, code/
├── review/   A.md, B.md, rebuttal.md（仅分歧时）
└── full-tests.log
```

### project-map.md（项目地图：项目的索引）

`PROJECT_ROOT/project-map.md` 是本 bundle 唯一要求主 agent 在业务仓库维护的持久化项目元数据。它是粗粒度的高层导航索引，内容可按项目形态取舍架构、选型、路由/API、公共组件、API auth 与领域关系；不追求全量覆盖，允许缺失，但不得记录与代码证据冲突的关系。领域关系以 LLM 可识别的领域对象为节点，只记录有路径证据的一跳直接生产者和直接消费者；数据库结构可发现领域对象和关联，但数据库结构不能单独证明生产者，不确定的关系直接省略。

地图仅缩小搜索空间，**不证明影响面完整，也不直接授权 scope**。普通任务只读且只作候选导航，发现地图缺失时只提示运行 `/plan-tdd-tasks init`；地图创建和更新仅由人工触发 `/plan-tdd-tasks init`，普通任务不创建、不更新，也不执行全局漂移判定。它是项目元数据而非规划产物，盲测者不读取 project-map.md。

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

**数据模式 `--list-changed`**（build-package.sh / stage-scope.sh 读取变更集的单一事实源，`--scope-file` 互斥）：

```text
check-scope.sh --project-root <dir> --base <rev> --list-changed
```

stdout 即数据（无状态行）：NUL 分隔记录 `M|<path>`（相对 base 的跟踪变更）与 `N|<path>`（未跟踪新文件），`.tmp/` 下路径无条件排除；成功 exit 0，用法/git 状态错误 exit 2。

### `run-full-tests.sh`

```text
run-full-tests.sh --project-root <dir> --test-cmd <string> [--workdir <dir>] [--log-file <path>]
```

`--test-cmd` 经 `sh -c` 执行（"全量"由主 agent 分析期确定并写入 `test-command.txt`，规则：必须覆盖仓库完整测试套件，禁止只跑新增测试）。相对 `--log-file` 始终以 `--project-root` 为基准解析，不受 `--workdir` 影响。输出与日志一致，末行状态。`test-command.txt` 为字面 `SKIP`（用户同意跳过测试）时主 skill 不调用本脚本：

| 退出码 | 状态行 |
|---|---|
| 0 | `run-full-tests: PASS` |
| 1 | `run-full-tests: FAIL (exit N)` |
| 2 | `run-full-tests: USAGE ERROR` |

### `check-env.sh`

```text
check-env.sh --project-root <dir> --base <rev> --branch <branch>
```

机械校验三条环境不变式（skill §2）：当前分支 == `--branch`（且非 main/master 保护分支）、工作树只含本任务改动（`.tmp/` 无条件排除）、`HEAD == --base`。任一破坏即 FAIL。末行状态：

| 退出码 | 状态行 |
|---|---|
| 0 | `env-check: PASS (branch <branch> at base)` |
| 1 | `env-check: FAIL (…)` |
| 2 | 用法/校验错误（stderr 报错） |

### `validate-ac.sh`

```text
validate-ac.sh --project-root <dir> --ac-file <path> --scope-file <path>
```

AC 语法承重墙机械校验（skill §4.1）：每条 AC 断言/归属/验证三字段齐备、验证 ∈ {unit, integration, scripted}、断言无禁用词（合理/适当/优雅/快速/尽可能/一些）、归属 ⊆ 范围声明、范围 `files:` 每个文件被 ≥1 条 AC 归属覆盖或列入 `infra:`。末行状态：

| 退出码 | 状态行 |
|---|---|
| 0 | `ac-check: PASS (n ACs, m declared)` |
| 1 | `ac-check: FAIL …` |
| 2 | 用法/校验错误（stderr 报错） |

### `parse-verdict.sh`

```text
parse-verdict.sh --verdict-file <path>
```

盲测 verdict 机械解析（skill §7/§8）：末行 `verdict: PASS` → PASS；末行 `verdict: FAIL` → 先回显 FAIL 块（`[AC-n] FAIL` 及其后紧跟的 `证据:` / `理由:` 行）再 FAIL；无合法 verdict 行、空文件或缺失文件 → MALFORMED。末行状态：

| 退出码 | 状态行 |
|---|---|
| 0 | `verdict-parse: PASS` |
| 1 | `verdict-parse: FAIL` |
| 2 | `verdict-parse: MALFORMED` |

### `build-package.sh`

```text
build-package.sh --project-root <dir> --package <dir> [--base <rev>]
```

§6 范围检查 PASS 后生成盲测包：`diff.txt` = `git diff <base>` + 每个未跟踪新文件追加块 `== new: <path> ==` 加完整内容；`code/` = 全部变更文件按仓库相对路径的完整副本（project-map.md 除外——项目元数据，非盲测输入；已删除文件无副本，删除在 diff.txt 中可见）。变更集来自 `check-scope.sh --list-changed`（单一事实源）。末行状态：

| 退出码 | 状态行 |
|---|---|
| 0 | `build-package: PASS (n files, m new)` |
| 1 | `build-package: FAIL (…)`（变更集读取失败） |
| 2 | 用法/校验错误（stderr 报错） |

### `stage-scope.sh`

```text
stage-scope.sh --project-root <dir> --package <dir> --base <rev> --branch <branch> --message <msg>
```

§9 提交收尾闸门，把全部收尾步骤机械化：防御性分支复检（当前分支 == `--branch` 且非 main/master 保护分支）→ `HEAD == base` → 再次运行 §6 的 check-scope.sh → 测试门禁（`test-command.txt` 为字面 `SKIP` 时以用户同意替代，中间行 `test gate: SKIP (user consent)`；否则 `<package>/../full-tests.log` 末行必须为 `run-full-tests: PASS`）→ 只 `git add` 变更集（check-scope PASS 保证变更集 ⊆ 范围声明）→ 暂存集 == 变更集验证（未声明暂存或遗漏变更都 FAIL）→ 恰好一次 `git commit -m <msg>`（消息由主 agent 组织）→ 工作树 clean 复检（`.tmp/` 除外）。末行状态：

| 退出码 | 状态行 |
|---|---|
| 0 | `stage-scope: PASS (commit <sha>)` |
| 1 | `stage-scope: FAIL (…)` |
| 2 | 用法/校验错误（stderr 报错） |

### `decide-verdicts.sh`

```text
decide-verdicts.sh --verdict-a <path> --verdict-b <path>
```

§8 分歧判定：内部以绝对路径调用 parse-verdict.sh 解析两份 verdict，按 2×2 矩阵分类，主 agent 不目测 pass/fail。MALFORMED 时点名出错文件，主 agent 只重派那一个盲测者（§7 末条）。末行状态：

| 退出码 | 状态行 |
|---|---|
| 0 | `decide-verdicts: DOUBLE-PASS`（双 pass → §9） |
| 1 | `decide-verdicts: DOUBLE-FAIL`（双 fail → 修复重派） |
| 1 | `decide-verdicts: SPLIT`（相左 → 自辩 + 用户仲裁） |
| 2 | `decide-verdicts: MALFORMED (<文件>)`（→ 只重派那一个） |

## 安装

```bash
git clone https://github.com/douxc/agent-dev-workflow.git
cd agent-dev-workflow
./install.sh
```

安装器把两个 skill 与两个 agent definitions 直接复制到每个**已存在**的平台根目录（`~/.claude`、`~/.claudeP`）的 `skills/` 与 `agents/` 下；平台根目录不存在时输出 `skip`，不会代为创建。源仓库是唯一 canonical 来源：不保留单独的 canonical 副本，不创建任何软链接；每次运行先删除旧目标再全新复制，可重复执行，不产生 `.backup.*`。

安装器**自动移除旧版遗留**（`skills/plan-dev-tasks`、`skills/dev-with-tdd` 及其 agent 文件），不触碰其他任何 skill 或 agent。已废弃的 `~/.claudeD` 平台根（若存在）被整体移除。所有校验（HOME、源文件、平台容器、settings 路径）在首次删除前完成；容器若是普通文件而非目录则 fail closed。未知参数报错。

安装器（plain 模式）还向用户级 `~/.claude/settings.json` 的 `permissions.allow` 合并两条读取规则 `` `Read(~/.claude/**)` `` 与 `` `Read(~/.claudeP/**)` ``，使任何项目里 skill reference 读取都不再弹窗；文件不存在时创建，保留既有内容，可重复执行且规则不重复。`~/.claude` 目录缺失时输出 `skip`，不代为创建；`python3` 不可用时输出 warning 并继续（不合并）；settings 内容损坏或路径是目录时 fail closed。`-p` 模式不触碰用户级 settings。

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

1. 读取 `references/permission-template.md`，将 `<PROJECT_ROOT>` 替换为项目根绝对路径去掉开头 `/` 的形式（配合模板 `//` 前缀）后展示完整规则——通用基线含 `` `Read(//<PROJECT_ROOT>/**)` ``、`` `Edit(//<PROJECT_ROOT>/**)` ``、`Bash(git:*)`、完整 `bash`/`sh`/`zsh` 放行、裸 `WebSearch`/`WebFetch`、`` `Read(~/.claude/**)` `` 与 `` `Read(~/.claudeP/**)` ``；按语言取舍含 `python3 -m unittest`/`npm test`/`cargo test`/`go test` 等测试命令；全部规则写入 allow、无保留询问分组；经用户同意后通过 `update-config` skill 写入 `.claude/settings.local.json` 的 `permissions.allow`（拒绝则跳过）；`update-config` 是可选宿主能力，本 bundle 无硬运行时依赖，skill 不可用时报告 `update-config unavailable; permission step skipped` 并继续其余步骤；**完成闸门**：权限步骤必须先完成（已写入 / 用户拒绝 / update-config 不可用）才进入步骤 2–4，完成前不得读取 `project-map.md`、不得执行漂移判断；
2. 生成 `project-map.md`（若不存在，按 `plan-tdd-tasks` skill §11.3 判定项目形态、自判类别，并总结领域对象及一跳直接生产者/直接消费者导航）；已存在时做**漂移判定**（核对机械可验证的现状事实，不做风格性改写），无漂移则报告无需更新，有漂移**经用户同意后更新**；数据库结构不能单独证明生产者，不确定的关系直接省略；
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
bash -n skills/plan-tdd-tasks/scripts/build-package.sh
bash -n skills/plan-tdd-tasks/scripts/stage-scope.sh
bash -n skills/plan-tdd-tasks/scripts/decide-verdicts.sh
bash -n skills/plan-tdd-tasks/scripts/check-env.sh
bash -n skills/plan-tdd-tasks/scripts/validate-ac.sh
bash -n skills/plan-tdd-tasks/scripts/parse-verdict.sh
sh -n skills/plan-tdd-tasks/scripts/run-full-tests.sh
git diff --check
```

端到端冒烟：在 scratch 仓库用一个玩具 feature 走完整流程——两个并行盲测子代理、verdict 落盘、盲测者只读（transcript 无写工具调用）、check-scope 抓越界编辑、提交盲测前全量经脚本跑 1 遍、仅最后 commit。可选：在本地 `settings.json` 预放行盲测者读包路径（如 `Read(//Users/<you>/**)`）以减少权限弹窗。

## 已知限制

- 脚本仅支持 macOS/Linux（bash/sh）。
- 静态盲测无法捕获运行时错误——由提交盲测前的全量测试兜底；盲测者之间可能相关性偏盲——由分歧自辩、人工仲裁与 2 轮上限兜底。
- 盲测者只读由 agent 定义的 `tools: Read, Grep, Glob` 在 harness 层强制；旧版 hooks 强制层不在本设计内（如需可作未来可选加固）。
- Hermes 平台：`install.sh -p <profile>` 互斥安装到命名 profile；主 skill 并行使用两个 `delegate_task` child，子代理继承父代理 toolsets（无只读参数），盲测者只读为**指令约束而非 harness 强制**，留待 VPS 实测。
