---
name: plan-tdd-tasks
description: 单 feature 开发全流程主 agent：分析、规划（AC 清单与范围声明）、准入闸门、TDD 实现与自测、机械范围检查、产出包、并行盲测复核、分歧处理、全量测试与提交。用户描述一个开发需求时使用；一次只处理一个 feature。
---

# 单 Feature 全流程：分析 → 规划 → TDD → 盲测 → 全量

本 skill 是单个 feature 开发任务的唯一执行者。所有工作在同一个会话中完成：分析、规划、准入闸门、TDD 实现与自测、机械范围检查、产出包、并行盲测、分歧处理、全量测试与提交。本 skill 无状态机、无版本号、无 gates；稳定性来自 AC 清单的质量、范围声明的机械检查与两个全新上下文的盲测者。本 skill 在业务仓库维护的唯一持久化项目元数据是 `${PROJECT_ROOT}/project-map.md`（§11）——它是项目的索引（地图），不承载任何规划状态。

## 1. 流程总览

```text
① 分析 → ② 规划（AC 清单 + 范围声明 + test-command.txt）
→ ③ 准入闸门（check-env.sh 环境不变式 + validate-ac.sh AC 校验）
→ ④ TDD 实现与自测 → ⑤ check-scope.sh 机械范围检查 → ⑥ 产出包
→ ⑦ 盲测 ×2（并行、只读、全新上下文）
→ ⑧ 分歧处理（双 pass 继续 / 双 fail 只给证据重修 / 相左自辩后人工）
→ ⑨ run-full-tests.sh 全量测试（每次尝试最后、1 遍）
→ ⑩ 最终范围复检 + git add 范围内文件 + 一次 commit → 清理 → 汇报
```

重跑上限：盲测最多 2 轮，超限强制人工（§10）。

## 2. 通用纪律

- 面向用户的自然语言使用简体中文；代码、标识符、命令与精确错误使用英文。
- **一次只处理一个 feature**。用户提出多个需求时，先确认优先级，逐个执行。
- **规划不落盘**：设计意图、实现思路、TDD 计划只存在于对话中，绝不写入任何文件。唯一落盘的规划产物是 AC 清单、范围声明与 test-command.txt（§4）。
- 任务期间**不得执行 `git commit`，不得执行 `git add`/stage**（§9 最终提交与 §12 init 收尾提交是仅有的例外）；不得 push。
- **分支策略**：main/master 是保护分支，不直接提交。开发基于最新 main checkout 一个临时分支（无长期 dev 分支）；开发、修复、调整完成后 commit 到该临时分支。由用户主动触发 merge 到 main；merge 完成后删除本地临时分支，main 始终保持最新且工作树 clean。任务开始前先基于最新 main checkout 一个临时分支；最终提交必须落在该临时分支。
- 任务开始前工作树必须 clean（`git status --porcelain` 为空）。非 clean 时先与用户确认基线：是并入本次任务还是先处理现有改动，确认前不开始。
- **环境不变式（三条）**：在临时分支上（§2 分支策略）；工作树只含本任务改动（`.tmp/<task-id>/` 除外）；`base` 与分支起点一致（`HEAD == base`）。任一破坏：立即**终止**流程并转人工处理，**不自愈**、不自行修复。由准入闸门的 `check-env.sh` 机械校验（§4.4）。
- 唯一临时目录：`${PROJECT_ROOT}/.tmp/<task-id>/`。任务开始前若存在同名残留，先与用户确认后删除。任务结束（含失败、放弃）后清理该目录。
- `${SKILL_ROOT}` 是包含当前已加载 `SKILL.md` 的目录。本 skill 的脚本固定为 `${SKILL_ROOT}/scripts/` 下五个：`check-scope.sh`、`run-full-tests.sh`（§6/§9）与 `check-env.sh`、`validate-ac.sh`、`parse-verdict.sh`（§4.4/§7），**以绝对路径调用**；禁止在业务仓库复制、改写或新建这些脚本，禁止探索业务仓库中的同名文件。

## 3. 分析

1. 确定 `PROJECT_ROOT`：`git rev-parse --show-toplevel`。
2. **快速地图索引（目标 10–20 秒，软预算）**：从需求提取 1–3 个领域关键词；`${PROJECT_ROOT}/project-map.md` 存在时只搜索一次 `project-map.md`，输出匹配的领域、生产者、消费者与路径，并统一标记为“待源码验证的导航候选”。索引阶段不展开源码、不递归关系、不确定最终 scope。地图未命中时立即进入下一步；文件不存在时只提示运行 `/plan-tdd-tasks init` 并继续，普通任务不创建或更新地图。
3. **源码分析（约 5 分钟，软预算）**：读取仓库指令（README、CONTRIBUTING 等），从地图候选开始验证并探索代码；地图不证明影响面完整，也不直接授权 scope。若一次工具调用跨过预算，在调用返回后进入检查点。
4. **人工检查点**：约 5 分钟仍未形成稳定范围时暂停，向用户汇报“已确认、已排除、未确认、残余风险”，让用户选择继续探索或接受当前范围。继续探索时追加一个 5 分钟窗口，窗口结束仍未收敛则再次询问；接受当前范围时仅以已确认内容生成 AC 和 scope，未确认项只保留在对话风险说明中，不得写入 AC/scope 或伪装成已确认事实。
5. **确定全量测试命令**：从 README、`package.json` scripts、`pyproject.toml`、Makefile 或既有测试目录推断仓库的完整测试套件命令；推断不出时直接询问用户。该命令稍后写入 `test-command.txt`，规则：**必须覆盖仓库完整测试套件，禁止只跑新增测试**；可以是复合命令（如 `python3 -m unittest discover && npm test`）。
6. 记录 `base = HEAD`（当前提交 sha，范围检查基线）。
7. 分析结论（目标、落点、测试命令、风险）只在对话中呈现，不落盘。普通任务不执行全局漂移判定，也不修改 project-map.md。

## 4. 规划

规划产物只有三个文件，全部写入 `${PROJECT_ROOT}/.tmp/<task-id>/package/`：

### 4.1 AC 清单（`ac-list.md`）—— 承重墙

```text
## AC 清单

- AC-1: 新增 hello() 函数，输入任意字符串 name，返回 "hello, <name>"。
  - 断言: hello("world") 的返回值等于 "hello, world"（精确字符串，大小写敏感）
  - 归属: src/greeter.py
  - 验证: unit
```

每条 AC 必须满足：

- **可观测行为**：一个 AC 一个行为。禁止复合 AC（同一句中用"并"连接多个行为）。
- **可验证断言**：命名真实标识符（函数、CLI、API 字段）+ 精确期望值。**禁止主观词**：合理、适当、优雅、快速、尽可能、一些。
- **归属**：逗号分隔的项目相对路径，每项必须是范围声明 `files:` 的条目。反向同样成立：范围声明 `files:` 的每个文件必须被至少一条 AC 的归属覆盖，或列入 `infra:`。
- **验证**：三选一 `unit | integration | scripted`，标签必须诚实（unit=无外部 IO；integration=子进程/文件/网络；scripted=仓库内脚本验证）。
- 编号 AC-1..AC-n 按实现顺序。

写完后逐条自查：断言是否机械可验证？归属是否与范围声明双向一致？任何一条不过就修改后再继续——**这一步决定盲测成败**。

### 4.2 范围声明（`scope.md`）—— 实现前写定，事后禁止修补

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

- `files:`：正授权清单，机械可执行。`infra:`：无 AC 断言的合理触碰项（配置、工具文件）。二者合计是 `check-scope.sh` 的声明集。
- `约束:`：对主 agent 的咨询性负约束，不机械执行。
- **范围声明一旦写出，不得事后修补以匹配实际改动**；发现需要扩大范围时按 §6 先回退再重新规划。

### 4.3 测试命令（`test-command.txt`）

恰好一行非空内容：§3 确定的全量测试命令。

### 4.4 准入闸门（环境 + AC 校验）

规划产物就绪、环境准备完成（基于最新 main checkout 临时分支，起点 = `base`，§3 步骤 6）后，进入 §5 之前先跑两个机械闸门；任一失败即**终止**流程转人工，不进入 §5：

1. **环境不变式**（§2 三条；任一破坏：**终止**、**不自愈**）：

```text
${SKILL_ROOT}/scripts/check-env.sh --project-root <PROJECT_ROOT> --base <BASE> --branch <BRANCH>
```

2. **AC 校验**（AC 语法承重墙机械校验；FAIL 即终止）：

```text
${SKILL_ROOT}/scripts/validate-ac.sh --project-root <PROJECT_ROOT> --ac-file <package>/ac-list.md --scope-file <package>/scope.md
```

两者都以绝对路径调用，退出码 0 才进入 §5 TDD。

## 5. TDD 实现与自测

- 严格 Red-Green-Refactor：先写一个失败测试并确认失败原因是行为缺失（Red）；再最小实现使其通过（Green）；仅在结构收益明确时重构，保持测试全绿。
- 迭代期间只运行**定向测试**（正在写的那个或邻近的测试），不跑全量；全量留给 §9。
- 不得为通过而削弱测试、不得删除失败的测试、不得跳过 Red 阶段。
- 实现只落在范围声明 `files:` + `infra:` 内的文件。
- **自解释代码**：实现开始前完整读取 `${SKILL_ROOT}/references/self-explaining-code.md`，实现必须满足该标准。发现任一 Bad 模式时先按 reference 重构，完成自检后才能进入 §6。

## 6. 机械范围检查与产出包

1. **先运行机械范围检查**（绝对路径）：

```text
${SKILL_ROOT}/scripts/check-scope.sh --project-root <PROJECT_ROOT> --scope-file <package>/scope.md --base <base>
```

- 退出码 0 = PASS：继续构建代码包。
- 退出码 1 = FAIL：先判断越界性质，禁止直接修改 scope.md 追认实际改动。
  - **偶发且非必要的越界**（日志、缓存、误编辑等）：删除新增文件或恢复误编辑，保持原 scope，重新运行本节范围检查；不重新规划、不重做已经完成的范围内实现。
  - **实现确实需要扩大范围**：先回退越界改动，回到 §4 重新规划并更新受影响 AC，再重新实现；scope.md 与代码保持“先声明、后实现”。
- 退出码 2 = 用法错误：修复参数或项目状态后重跑。

产出包布局：

```text
.tmp/<task-id>/package/
├── ac-list.md
├── scope.md
├── test-command.txt
├── diff.txt
└── code/                # 全部变更文件的完整副本（仓库相对布局）
```

范围检查 PASS 后才执行以下步骤：

1. 生成 `diff.txt`：`git diff <base>` 输出跟踪文件变更；对每个未跟踪新文件追加块 `== new: <path> ==` 加完整内容。`code/` 是盲测者的事实来源，`diff.txt` 仅作辅助。
2. 构建 `code/`：将范围检查确认的变更文件逐一复制到 `code/` 下对应相对路径（project-map.md 除外——项目元数据，非盲测输入，不进入 `code/`，§11）。

## 7. 盲测派发

- 先按当前宿主选择原生子代理传输，不得混用：
  - **Claude Code**：在**同一条消息**中并行派发两个 `Agent(blind-review-tasks)` custom agent。
  - **Hermes**：在同一轮中并行发起两个 `delegate_task` child；每个 child 的任务开头要求加载 `blind-review-tasks` skill，并严格遵守其静态只读规则。Hermes child 继承父代理 toolsets，盲测者只读是**指令约束而非 harness 强制**，即使写入或执行工具可见也不得使用。
  - 当前宿主传输不可用、无法创建两个全新上下文或无法认证结果来源时 **fail closed**：停止流程并向用户报告，不得在主上下文中冒充盲测者。
- 两个子代理必须并行、使用全新上下文且互不共享。
- 每个子代理的 prompt 只包含：package 绝对路径 + PROJECT_ROOT（仅作只读上下文）+ 一句话指令"按已加载的 blind-review-tasks skill 输出 verdict"。
- **不得**在 prompt 中传递任何设计意图、实现思路或"我认为实现是对的"之类的立场。
- 子代理的最终输出即 verdict；分别保存到 `${PROJECT_ROOT}/.tmp/<task-id>/review/A.md` 与 `review/B.md`。
- 先等两个 verdict 都收到再判断。收到空结果或明显非 verdict 格式的结果时，只重派那一个子代理（新上下文），不整轮重跑。

## 8. 分歧处理

| A \ B | pass | fail |
|---|---|---|
| pass | → §9 全量测试 | → 自辩（下） |
| fail | → 自辩（下） | → 双 fail（下） |

- **双 fail**：只读取两份 verdict 的证据，**禁止反驳**（不辩解、不质疑检查项合理性）。逐条修复后回到 §6 重新产出包并重派盲测（全新上下文），轮次 +1。若修复过程中发现需要改变范围或新增 AC，先走 §6 的回退重规划。
- **一 pass 一 fail（相左）**：主 agent 自辩。对每个争议检查项写 `${PROJECT_ROOT}/.tmp/<task-id>/review/rebuttal.md`：逐条给出"接受+修复方案"或"反驳+包内路径证据"。然后将两份 verdict 与 rebuttal 一并**呈交用户仲裁**；以用户裁决为准，不得自行判定胜负。

## 9. 全量测试与提交

1. 双 pass 后运行全量测试（绝对路径，每次尝试最后执行、恰好 1 遍）：

```text
${SKILL_ROOT}/scripts/run-full-tests.sh --project-root <PROJECT_ROOT> --test-cmd "$(cat <package>/test-command.txt)" --log-file <package>/../full-tests.log
```

2. `run-full-tests: PASS` 后进入提交收尾：
   - **防御性复检**：确认当前分支不是 main（§2 分支策略，main 是保护分支）；在 main 时停止并转人工；
   - 再次运行 §6 的 check-scope.sh；只有退出码 0 才继续，失败按 §6 分流；
   - `git add` 只加范围声明内的文件（`files:` + `infra:`）；
   - 一次 `git commit`，信息包含 task 名与 AC 范围；
   - 确认工作树 clean（`git status --porcelain` 为空，`.tmp/` 除外）。
3. 清理 `${PROJECT_ROOT}/.tmp/<task-id>/`，向用户汇报：AC 清单、两份 verdict 摘要、全量结果、commit sha。
4. 全量测试 FAIL：保留 `full-tests.log`，按修复是否改变盲审事实分流；全量失败不应通过扩大范围声明掩盖。
   - **代码、测试、AC 或 scope 发生变化**：回到 §6 重新检查并产包，再到 §7 重新派发全新盲测者（不得复用上一轮），轮次 +1。
   - **只有环境或测试命令变化且代码包未变**：保留上一轮双 PASS，修复环境或 `test-command.txt` 后直接重试本节全量测试，不消耗盲测轮次。环境或测试命令修复最多重试 2 次；连续失败后停止并转人工处理。

## 10. 重跑上限

- 盲测重跑最多 **2 轮**：第 1 轮双 fail → 修复 → 第 2 轮；第 2 轮仍双 fail → **强制人工**：呈交两份 verdict 与修改摘要，由用户选择（继续修 / 接受现状 / 放弃任务）。超过上限自动停止，不得自行开始第 3 轮。
- 任意一轮出现相左 → 按 §8 自辩后人工仲裁，仲裁结果不消耗重跑轮次。
- 全量测试失败后，只有代码包事实变化而触发的重派计入轮次上限。

## 11. project-map.md（项目地图：项目的索引）

### 11.1 目的与语义

`${PROJECT_ROOT}/project-map.md` 是本 skill 在业务仓库维护的唯一持久化项目元数据。它是**项目的索引（地图）**：让后续 agent 快速熟悉项目、确认变更文件。生成或更新时须向 agent 说明这一目的。

它只提供粗粒度的高层导航：允许分类宽、描述粗或信息缺失，不追求全量覆盖；不得记录与代码证据冲突的关系。地图是待验证候选来源，**不证明影响面完整，也不直接授权 scope**。

它是项目**现状事实**的记录（描述项目是什么），**非规划产物**：设计意图、实现思路、TDD 计划、风险分析仍只存在于对话中（§2），绝不写入。**非迭代记录**：不含任务历史、测试命令等操作元数据。

**内容准入标准**：只写入方便其他 agent 使用、有价值的内容（能帮助快速熟悉项目或确认变更范围的事实）；无此价值的琐碎内容不写入。

### 11.2 位置、版本控制与盲测隔离

- 位置：`${PROJECT_ROOT}/project-map.md`（仓库根），随项目提交进 git；不放在 `.tmp/`。
- project-map.md 不复制进 `code/`（§6）；盲测者不读取 project-map.md，其判断只来自 AC 清单、范围声明与代码包。

### 11.3 内容与格式

```text
# project-map
## <类别>

<项目现状事实>
```

- 参考类别清单（**非必填、可取舍**）：`架构`、`选型`、`前端路由`、`后端 API`、`公共组件`、`API auth`。
- 可增加 `领域关系` 类别，以 LLM 可识别的领域对象为节点，只记录有可定位路径证据的直接生产者与直接消费者。一跳关系只作导航，不递归展开依赖。
- **形态适配**：前后端分离项目——前端/后端分节描述（如 `前端选型`、`前端路由`、`后端选型`、`后端 API`）；前后端一体项目——合并描述（如 `路由/API`）。
- init 模式的主 agent **判定项目形态并自判取舍**：写入哪些类别、每节写哪些事实，以内容准入标准为准；不在清单或自判范围的内容不写入。普通任务只读取，不写入。

### 11.4 时机

| 时机 | 环节 | 触发条件 | 动作 |
|---|---|---|---|
| 读取时机 | §3 步骤 2 | 文件存在 | 快速搜索一次，输出待源码验证的导航候选 |
| 文件不存在 | §3 步骤 2 | 普通任务 | 只提示运行 `/plan-tdd-tasks init`，继续任务，不创建地图 |
| 创建与更新 | §12 init 模式 | 仅由人工触发 `/plan-tdd-tasks init` | 按 `references/init.md` 生成或执行全局漂移判定；普通任务不创建或更新 |

## 12. init 模式（初始化，非任务）

- 仅字面 `/plan-tdd-tasks init`（skill args 恰为 `init`）进入 init 模式；其他调用均走普通任务流程。
- 触发后必须完整读取 `${SKILL_ROOT}/references/init.md` 并按其规则执行。
- **init 不是任务**：无 AC、scope、盲测、TDD 或 `.tmp/` 产物；不进入 §2–§10，结束时工作树必须 clean。
