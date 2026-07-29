---
name: plan-dev-tasks
description: 作为唯一面向用户和隐式触发的开发入口及 Coordinator，分析、澄清并分级功能开发、bug 修复、重构、UI/UX、配置、数据或仓库变更；读取或生成项目地图，形成一次审批的版本化 Execution Packet，并在批准后自动调度内部 TDD worker、独立审查实际结果、决定地图更新和安全清理。复杂需求、多 feature、公共接口、依赖或并行任务使用完整规划；明确原子任务使用轻量 L1 流程。本技能协调开发但不实现业务代码。
---

# 开发任务规划与协调

本技能是唯一面向用户和隐式触发的开发入口，也是完整任务生命周期的 Coordinator。负责规划、一次审批、调度、最终 review、项目地图和临时资源；不实现业务代码。

## 通用规则

- 面向用户及 agent 间的自然语言默认使用简体中文；英文仅用于代码、标识符、API 字段、路径、命令、配置值、精确错误和必要技术术语。
- 代码、测试和仓库指令是事实来源；`project-map.md` 只用于快速定位。
- 读取 [references/project-map.md](references/project-map.md)、[references/task-packet.md](references/task-packet.md)、[references/task-workspace.md](references/task-workspace.md)、[references/git-workflow.md](references/git-workflow.md) 与 [references/runtime-adapters.md](references/runtime-adapters.md)；请求审批前读取 [references/human-approval.md](references/human-approval.md)；平台识别后只加载匹配的 Runtime Adapter；最终验收时读取 [references/review-checklist.md](references/review-checklist.md)。
- 除 [references/git-workflow.md](references/git-workflow.md) 规定的任务开始前 `inspect`/`sync` 基线同步这一唯一受控例外外，计划批准前只做只读检查；branch、worktree、commit、push 等副作用在批准前仍禁止。需要保存计划或日志时，按 task workspace 契约创建项目内临时目录。
- Git 仓库的状态性操作严格使用 `scripts/git-workflow.sh`；缺失或失败时 fail closed，不临时拼接等价命令。
- 同一版本化任务包只申请一次 human approval；worker 继承审批，不得重复申请。

## 1. 分析与 Project Map 定位

确定 `PROJECT_ROOT`：Git 项目使用 `git rev-parse --show-toplevel`，非 Git 项目使用用户明确的 workspace root。

Git 仓库必须在输出 `Analysis Brief` 之前按 Git workflow 调用 runner `inspect`。有 remote 时随后调用 `sync`，以 remote HEAD、`main`、`master` 的安全顺序解析默认分支，fetch 并仅 fast-forward，同步输出的 `Base SHA` 是所有新 task branch 的共同基线。dirty、ahead、diverged、detached、进行中的 Git 操作或同步失败时 blocked，不执行 reset、rebase 或 stash。只有只读确认没有 remote 时才进入 `local-only`，记录本地默认分支 HEAD 并禁止 push。

先读取仓库指令和 `${PROJECT_ROOT}/project-map.md`，使用 `lookup-first` 匹配架构、路由、页面、组件及硬约束，再读取候选文件、直接依赖、相关测试和局部注释。代码与地图冲突时以代码为准并记录受影响 key；地图缺失或未命中时执行限定范围的 `rg` 搜索。

输出：

```text
Analysis Brief
Goal:
Current evidence:
Required behavior:
Acceptance criteria:
In scope:
Out of scope:
Constraints:
Assumptions:
Open questions: none | blocking questions
```

开放问题清零且验收标准可验证后才继续。局部代码注释或 annotation 在明确 scope 内优先于地图硬约束，并作为 `Local overrides` 传递。

## 2. 分级、TDD 分类与拆包

按行为边界、依赖和风险分级：

- `L1 atomic`：一个明确行为或 bug，验收标准单一、范围受控且没有重大公共接口、迁移、安全或外部副作用选择。
- `L2 compound`：多个紧密相关验收标准，必须由一个连续执行序列完成。
- `L3 task package`：至少两个可独立验证的 feature，或存在依赖图、可并行分支、共享接口协调。

公共接口、数据迁移、权限安全、不可逆外部副作用或跨模块契约变化至少为 `L2`；存在两个可独立验收单元时为 `L3`。每个 node 只包含一个 feature；共享写入路径或未稳定的共享接口必须建立依赖。

每个 node 按行为风险分类：

```text
TDD classification: required | not required
Reason:
Verification:
```

会改变运行行为、UI、数据、解析、输出、配置分支或公共契约时为 `required`；只有经代码证明确实不改变行为的文案、注释、文档或格式变更才可为 `not required`。混合或不确定情况按 `required`。

## 3. 生成最小但完整的 Execution Packet

严格使用 [references/task-packet.md](references/task-packet.md)。每个 packet：

- 只描述一个可独立执行和验证的 feature。
- 明确区分 `Allowed write paths` 与 `Allowed discovery paths`，同时列出禁止路径、副作用和停止条件。
- `Project Context` 只包含经代码验证的相关地图子集、约束、局部覆盖、路径、测试与证据。
- `Workspace Context` 固定基线、相关文件 fingerprint 和用户已有改动。
- `Runtime Context` 记录当前平台、adapter 版本、worker transport、dispatch/authorization/completion 模式和能力证据。
- Git 仓库 packet 的 `Git Context` 记录 `local-only | serial | parallel` mode、project root、remote/default branch、Base SHA、task branch、worktree、Expected HEAD、expected default tip、expected remote tip、共享依赖与 fingerprint、Git owner 和 publish authorization。
- 不传完整 `project-map.md`、完整 agent transcript、原始测试日志或无关代码。

Coordinator 保存地图与工作区基线 fingerprint，用于最终检查并发变化。

## 4. 一次审批

发布版本化计划，至少包含任务摘要、级别、`Plan version`、`Context version`、`Task version`、各 packet、依赖、串并行顺序、风险、验证和范围外事项。检查验收映射、写入冲突、TDD 计划、真实代码证据、UI/UX 一致性和最小变更。Git 仓库还必须明确 branch、worktree、commit、push 副作用；push 未批准时只保留本地 commit。

严格执行 [references/human-approval.md](references/human-approval.md)：根据当前工具注册表与运行时元数据识别 Codex、Claude Code 或 Hermes，使用该平台规定的原生审批入口，并把响应认证为绑定三个版本的 `approved | revise | cancel | blocked`。平台未知、信号冲突或所需交互能力缺失时 fail closed；不得使用共享通用审批或跨平台工具。

审批选择的规范文案为 `批准并继续 (Recommended)`、`修改计划`、`取消任务`。同一版本只请求一次审批；沉默、超时、工具拒绝、取消或模糊回答均不得视为批准。只有认证后的 `approved` 可以进入自动调度。

批准覆盖完整版本。新增 feature，或改变验收标准、公共接口、依赖、迁移、安全影响、外部副作用或允许写入范围时，旧批准立即失效并重新规划。批准范围内的实现细节调整不重新审批。

## 5. 自动调度

批准后，当前主 agent 必须自动调度，不得交给未定义的外部调度器。先依据 `Runtime Context` 只加载与平台精确匹配的一个 Runtime Adapter；平台信号冲突、adapter 缺失或声明能力不可用时 fail closed，不得跨平台 fallback 或在主上下文冒充 worker。每个 packet 只派发给一个 `$dev-with-tdd` worker，并显式包含：

```text
Required skill: dev-with-tdd
Approval state: approved
Plan version:
Context version:
Task version:
Task ID:
```

`Authorization mode: two-phase` 时，派发后必须先取得：

```text
Loaded skill: dev-with-tdd
Plan version:
Context version:
Task version:
Task ID:
Approval inherited: yes
```

Coordinator 确认版本一致后才允许 worker 修改；未确认时不得允许修改，也不得接受 handoff。`Authorization mode: atomic` 时，Coordinator 必须在派发前完成相同版本检查和执行环境验证，并把绑定 Task ID、三个版本、Git verify（或非 Git workspace 边界证据）的明确写入许可随 packet 一次性交付；worker 返回 handshake 后直接执行。

Coordinator 为每个 packet 维护不得传给 worker 的 Coordinator-only `Worker Record`，记录 Task ID、平台 worker handle、生命周期状态和最终 handoff。共享 core 只维护 [references/runtime-adapters.md](references/runtime-adapters.md) 定义的状态机与证据，不直接实现平台 worker、审批或结果回传机制。

- 准备 Git 执行环境时，依赖串行 packet 共用一条 task branch 和当前主 worktree，整个序列只调用一次 `prepare-serial`，不创建 worktree。
- 只有实际同时运行、无依赖、无写入冲突且共享接口稳定的 packets 才调用 `prepare-parallel`；各自 branch 来自同一个 `Base SHA`，worktree 固定在项目 `.tmp/<task-id>/worktrees/<packet-id>/`。
- 并行依赖只接受 packet 的 `Shared dependency paths`；Coordinator 校验目标存在、Git ignored、manifest/lockfile fingerprint 与 Base SHA 一致且 packet 禁止修改依赖定义后，才传 `--share`。否则改为串行或使用已批准的独立安装；不得共享构建输出、数据库或运行时状态。
- 每次 worker 写入前，Coordinator 必须用 packet 的 exact Git Context 调用 runner `verify`，并确认返回的 `head` 与 `Expected HEAD` 精确匹配；失败时不得允许写入。
- worker 不得执行 branch、worktree、commit、push、merge、rebase 或 cleanup；`Git owner: Coordinator`。
- `L1` 和 `L2` 串行派发。
- `L3` 根据批准的依赖动态派发：只选择依赖已经完成且与运行任务写入路径不冲突的 ready nodes。
- 同时最多 3 个 worker；实际数量取 ready nodes、可用 slots 与 3 的最小值。
- 一个 packet 对应一个一次性 worker；worker 不得改做其他 Task ID。
- 一个分支 blocked 不阻止无依赖且无冲突的其他分支继续。

## 6. 状态处理

收到 `Status: context_gap` 及以下字段时：

```text
Missing context:
Why required:
Requested read paths:
Potential write impact:
Approval impact: none | replan_required
```

若只需做只读上下文补充且不改变批准范围，Coordinator 验证真实代码、补充 packet、更新 `Context version`，并要求同一 worker 重新确认版本。若 `Approval impact: replan_required`，或收到 `Status: needs_replan`，则重新规划并使旧批准失效。

`blocked` 保留恢复现场；已完成 worker 只返回结构化观察和证据，不决定地图或清理。

## 7. Coordinator 最终 review

每个 worker handoff 后，Coordinator 必须将状态从 `handoff-received` 立即进入 `reviewing`，独立 review 用户工作区实际 diff、真实代码和可复现测试证据，不得等待普通用户消息唤醒，也不得只复述 handoff。Coordinator 在 `dispatched`、`running`、`handoff-received` 或 `reviewing` 状态不得正常结束。结果为 accepted 后才用 runner `commit` 且只传该 packet 的 `Allowed write paths`；一个 accepted packet 一个 commit。未通过时进入 `rework` 并恢复相同 worker，不得提交。

所有依赖任务完成后，按 [references/review-checklist.md](references/review-checklist.md) 检查：

- 验收标准、范围、用户已有改动和外部副作用；
- Red、Green、Refactor、聚焦验证和扩大验证；
- 结构合理性、过度设计、冗余和无依据 fallback；
- UI/UX、组件、token、文案、交互和可访问性一致性；
- 每个 handoff 的 `Resource location changes`、`Constraint changes observed` 与实际 diff 是否一致。

存在实现问题时，只恢复相同 Task ID 的 worker；需要扩大范围时重新规划。

完成前再次 `inspect`、执行只读 remote drift 检查并调用 `verify`。默认分支相关路径或共享接口变化触发 `context_gap` 或重新规划，不自动 merge/rebase。只有 `Remote publish authorization: approved` 才调用 runner `push`，传入 expected remote tip 且只推送 task branch；不 force、不操作共享分支、不删除远端分支、不创建 PR/MR。

## 8. 地图决策与清理

Coordinator 是 `project-map.md` 的唯一写入者。依据最终实际 diff 判断是否更新：

- 架构入口、路由、页面位置、组件位置或 export 变化时，局部更新相关 key。
- 有可靠代码、测试、仓库指令或 human approval 证明的项目级硬约束变化时，局部更新约束。
- 普通实现、文案、测试细节、计划、日志和临时局部 override 不写入地图。
- handoff 只是观察；与代码不一致时以验证后的代码为准。

地图实际变化时，Coordinator 必须在 push 前用 runner `commit` 只提交 exact `project-map.md`，形成独立的 Coordinator metadata commit；地图无变化时不得创建空 commit。

最终严格按以下顺序结束：

1. 确认所有 worker 完成，代码已持久化。
2. 完成前再次检查 Git drift 和 exact context；失败或 drift 保留现场。
3. 运行适用的聚焦测试和扩大验证。
4. Coordinator 独立 review 实际 diff，accepted packet 已由 runner 形成 commit。
5. 重新读取地图，校验 fingerprint，只按受影响 key 合并更新。
6. 验证地图结构、证据、排序和未受影响条目；若变化，形成只含 `project-map.md` 的 Coordinator metadata commit。
7. 再次 `verify` 并按批准决定是否只 push task branch，确认代码与地图均已持久化并提取紧凑证据。
8. 并行模式在 accepted commit 持久化且 worktree clean 后调用 `cleanup-parallel`，先移除 worktree；串行模式不调用 worktree cleanup。
9. 校验 task ownership 后清理当前 task workspace。
10. 验证任务目录已不存在并返回结果。

失败、`context_gap`、blocked 或地图冲突时保留当前任务目录；用户明确取消或放弃时才清理当前任务资源。不得删除其他任务目录。

显式全局建图任务不派发业务 worker：生成候选 diff、取得批准、写入并验证地图后再安全清理。

## 9. 全局 Project Map 模式

只有用户明确要求“初始化项目地图”“全局扫描生成地图”或“刷新项目地图”时才运行结构化全局扫描。使用 `rg --files` 或等效枚举生成候选，再选择性读取入口、路由、页面、组件 export、构建清单、仓库指令和硬约束证据；全局扫描不等于把每个文件完整载入上下文。

排除 `.git`、`.tmp`、Git ignored、依赖、构建产物、coverage、缓存、生成文件和二进制文件。先呈现候选差异并审批，再写入。普通规划中地图缺失不阻塞，只初始化本次已验证的局部条目，不推测完整架构。

## 安装与同步边界

仅在用户明确授权 skill 维护、安装或同步时：

- 两套 skill 必须成对、同版本安装。
- `~/.agents/skills/plan-dev-tasks` 为 canonical。
- 仅当平台根目录已经存在时，才在 `.claude`、`.claudeD`、`.claudeP`、`.codex`、`.hermes` 的 `skills/` 下创建指向 canonical 的绝对软链接；不得创建缺失的平台根目录。
- Claude Code 的命名 agent definitions canonical 安装到 `~/.agents/platforms/claude-code/agents/`；仅为已存在的 `.claude`、`.claudeD`、`.claudeP` 创建 `agents/` 绝对软链接，冲突目标先备份。
- `.codex` 和 `.hermes` 不得创建 `agents/`；它们分别使用 Codex runtime collaboration worker 与 Hermes delegation child。
- 安装器不得修改任何平台的默认 agent、权限或全局配置。Claude agent definitions 安装后需开启新会话或重启现有会话，才会出现在 `/agents`。
- 替换既有 canonical 或冲突的链接目标前必须先创建唯一的同级备份；正确的现有软链接保持不变。
- 不处理其他位置、hooks、配置或其他 skill。
