---
name: plan-tdd-tasks
description: 单 feature 开发全流程主 agent：分析、规划（AC 清单与范围声明）、TDD 实现与自测、产出包、机械范围检查、并行盲测复核、分歧处理、全量测试与提交。用户描述一个开发需求时使用；一次只处理一个 feature。
---

# 单 Feature 全流程：分析 → 规划 → TDD → 盲测 → 全量

本 skill 是单个 feature 开发任务的唯一执行者。所有工作在同一个会话中完成：分析、规划、TDD 实现与自测、产出包、机械范围检查、并行盲测、分歧处理、全量测试与提交。本 skill 无状态机、无版本号、无 gates、无 project map；稳定性来自 AC 清单的质量、范围声明的机械检查与两个全新上下文的盲测者。

## 1. 流程总览

```text
① 分析 → ② 规划（AC 清单 + 范围声明 + test-command.txt）→ ③ TDD 实现与自测
→ ④ 产出包 + check-scope.sh 机械范围检查
→ ⑤ 盲测 ×2（并行、只读、全新上下文）
→ ⑥ 分歧处理（双 pass 继续 / 双 fail 只给证据重修 / 相左自辩后人工）
→ ⑦ run-full-tests.sh 全量测试（最后、1 遍）
→ ⑧ git add 范围内文件 + 一次 commit → 清理 → 汇报
```

重跑上限：盲测最多 2 轮，超限强制人工（§10）。

## 2. 通用纪律

- 面向用户的自然语言使用简体中文；代码、标识符、命令与精确错误使用英文。
- **一次只处理一个 feature**。用户提出多个需求时，先确认优先级，逐个执行。
- **规划不落盘**：设计意图、实现思路、TDD 计划只存在于对话中，绝不写入任何文件。唯一落盘的规划产物是 AC 清单、范围声明与 test-command.txt（§4）。
- 任务期间**不得执行 `git commit`，不得执行 `git add`/stage**（§8 最终提交是唯一例外）；不得 push。
- 任务开始前工作树必须 clean（`git status --porcelain` 为空）。非 clean 时先与用户确认基线：是并入本次任务还是先处理现有改动，确认前不开始。
- 唯一临时目录：`${PROJECT_ROOT}/.tmp/<task-id>/`。任务开始前若存在同名残留，先与用户确认后删除。任务结束（含失败、放弃）后清理该目录。
- `${SKILL_ROOT}` 是包含当前已加载 `SKILL.md` 的目录。本 skill 的脚本固定为 `${SKILL_ROOT}/scripts/check-scope.sh` 与 `${SKILL_ROOT}/scripts/run-full-tests.sh`，**以绝对路径调用**；禁止在业务仓库复制、改写或新建这两个脚本，禁止探索业务仓库中的同名文件。

## 3. 分析

1. 确定 `PROJECT_ROOT`：`git rev-parse --show-toplevel`。
2. 读取仓库指令（README、CONTRIBUTING 等）与项目结构，理解 feature 的落点。
3. **确定全量测试命令**：从 README、`package.json` scripts、`pyproject.toml`、Makefile 或既有测试目录推断仓库的完整测试套件命令；推断不出时直接询问用户。该命令稍后写入 `test-command.txt`，规则：**必须覆盖仓库完整测试套件，禁止只跑新增测试**；可以是复合命令（如 `python3 -m unittest discover && npm test`）。
4. 记录 `base = HEAD`（当前提交 sha，范围检查基线）。
5. 分析结论（目标、落点、测试命令、风险）只在对话中呈现，不落盘。

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

## 5. TDD 实现与自测

- 严格 Red-Green-Refactor：先写一个因行为缺失而失败（Red）的测试，记录命令与失败原因；再最小实现使其通过（Green）；仅在结构收益明确时重构，保持测试全绿。
- 迭代期间只运行**定向测试**（正在写的那个或邻近的测试），不跑全量；全量留给 §7。
- 不得为通过而削弱测试、不得删除失败的测试、不得伪造 Red 记录。
- 实现只落在范围声明 `files:` + `infra:` 内的文件。

## 6. 产出包与机械范围检查

产出包布局：

```text
.tmp/<task-id>/package/
├── ac-list.md
├── scope.md
├── test-command.txt
├── diff.txt
└── code/                # 全部变更文件的完整副本（仓库相对布局）
```

1. 生成 `diff.txt`（机械步骤）：`git diff <base>` 输出跟踪文件变更；对每个未跟踪新文件追加块 `== new: <path> ==` 加完整内容。`code/` 是盲测者的事实来源，`diff.txt` 仅作辅助。
2. 构建 `code/`：将范围检查确认的变更文件逐一复制到 `code/` 下对应相对路径。
3. 运行机械范围检查（绝对路径）：

```text
${SKILL_ROOT}/scripts/check-scope.sh --project-root <PROJECT_ROOT> --scope-file <package>/scope.md --base <base>
```

- 退出码 0 = PASS：继续。
- 退出码 1 = FAIL（存在 `out-of-scope` 文件）：**先回退越界改动**（恢复被改文件、删除越界新增文件），然后**回到 §4 重新规划**（改写范围声明与受影响的 AC 归属），再重新实现。**禁止直接修改 scope.md 以匹配实际改动**；scope.md 与代码是"先有声明、后有实现"的关系。
- 退出码 2 = 用法错误：检查参数与项目状态，修复后重跑。

## 7. 盲测派发

- 在**同一条消息**中并行派发两个 `Agent(blind-review-tasks)` 子代理（全新上下文，互不共享）。
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

1. 双 pass 后运行全量测试（绝对路径，最后执行、恰好 1 遍）：

```text
${SKILL_ROOT}/scripts/run-full-tests.sh --project-root <PROJECT_ROOT> --test-cmd "$(cat <package>/test-command.txt)" --log-file <package>/../full-tests.log
```

2. `run-full-tests: PASS` 且范围检查仍为 PASS → 提交：
   - `git add` 只加范围声明内的文件（`files:` + `infra:`）；
   - 一次 `git commit`，信息包含 task 名与 AC 范围；
   - 确认工作树 clean（`git status --porcelain` 为空，`.tmp/` 除外）。
3. 清理 `${PROJECT_ROOT}/.tmp/<task-id>/`，向用户汇报：AC 清单、两份 verdict 摘要、全量结果、commit sha。
4. 全量测试 FAIL：修复问题后**回到 §7 重新派发全新盲测者**（不得复用上一轮盲测者），轮次 +1，保留 `full-tests.log` 供诊断。全量失败不应通过扩大范围声明掩盖。

## 10. 重跑上限

- 盲测重跑最多 **2 轮**：第 1 轮双 fail → 修复 → 第 2 轮；第 2 轮仍双 fail → **强制人工**：呈交两份 verdict 与修改摘要，由用户选择（继续修 / 接受现状 / 放弃任务）。超过上限自动停止，不得自行开始第 3 轮。
- 任意一轮出现相左 → 按 §8 自辩后人工仲裁，仲裁结果不消耗重跑轮次。
- 全量测试失败后的重派同样计入轮次上限。
