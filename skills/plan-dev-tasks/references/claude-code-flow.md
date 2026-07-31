# Claude Code 平台流程

本文件是 Claude Code 平台的具体执行流程，把平台无关的状态机、Execution Packet、Git workflow、审查与清理契约（见 [SKILL.md](../SKILL.md)、[git-workflow.md](git-workflow.md)、[task-packet.md](task-packet.md)、[review-checklist.md](review-checklist.md)）映射到 Claude Code 原生能力。加载条件是已按 capability 选定本 flow。

```text
Runtime Context:
  Platform: claude-code
  Platform flow: claude-code-flow.md
  Worker transport: Agent(dev-with-tdd)
  Dispatch mode: foreground | background-aggregate
  Authorization mode: atomic
  Completion mode: foreground Agent result | host completion notification + result aggregation
  Capability evidence: authenticated Claude Code runtime metadata, registered Agent tool, named dev-with-tdd custom agent, and proven result return path
```

## Human approval

计划审批沿用 [human-approval.md](human-approval.md)：Plan mode 使用 `ExitPlanMode`，非 Plan 场景使用 `AskUserQuestion`。审批能力、custom agent 可见性和结果回传能力必须分别验证。

每个传给 `ExitPlanMode` 的审批计划正文必须包含 `Plan version:`、`Context version:`、`Task version:` 与 post-approval gate continuation；批准事件只进入 `approved`，不得授予 Coordinator 业务写权限。

Coordinator 派发前必须取得最小能力证据：

- 当前宿主的认证运行时元数据指向 Claude Code，且没有冲突的平台信号；
- `Agent` 工具当前可用，且名为 `dev-with-tdd` 的 custom agent 已加载；
- 串行任务能以前台 Agent 返回的 returned result 恢复当前 Coordinator；
- 并行任务还必须证明每个后台 Agent 的结果可被显式聚合并重新注入当前 Coordinator。

必要能力缺失、custom agent 未加载、返回来源不确定或平台信号冲突时 fail closed。不得用普通 skill 加载动作冒充独立 worker transport，也不得在共享主上下文直接实现后伪造 handoff。

## Post-approval dispatch gate

`ExitPlanMode` 或 `AskUserQuestion` 的批准事件只进入 `approved`，不得授予 Coordinator 业务写权限。派发路径固定为 `approved -> gate（完成 verify） -> prepared -> Agent(dev-with-tdd) -> dispatched -> authorized -> running`。gate 是派发前的 Claude Code checkpoint，执行 SKILL.md 定义的全部 gate 不变量。

Coordinator 必须为每个 packet 形成以下 gate record，任一字段缺失或与批准的 Execution Packet 不一致时 fail closed：

```text
Post-approval dispatch gate:
  Approval event: ExitPlanMode approved | AskUserQuestion approved
  Plan version:
  Context version:
  Task version:
  Task ID:
  Coordinator write authority: none
  Environment verification:
  Dispatch mode: foreground | background-aggregate
  Worker transport: Agent(dev-with-tdd)
```

gate 严格按下列顺序执行：

1. 认证 approval event，并核对 `Plan version`、`Context version`、`Task version`、`Task ID`、批准的 `Dispatch mode` 和 `Worker transport`。
2. 确认 `Coordinator write authority: none`。批准不允许 Coordinator 直接编辑业务文件、运行会产生业务 diff 的实现工具或伪造 worker handoff。
3. 在任何实现工具前，Git 项目必须立即通过 bundled runner `verify --require-clean` 核对 exact Worktree、Task branch、Expected HEAD、Base SHA 和 clean 状态；非 Git 项目必须重新核对批准时的 workspace fingerprint、允许路径与边界。
4. 若验证发现批准后新增业务 diff，立即转为 `blocked`，原因固定为 `coordinator_direct_write`，保留现场，并用 runner `state --to blocked` 记录该原因。不得 rollback、不得 stash、不得 clean、不得 commit，也不得标记为 `accepted`。
5. verify 必须先于 `prepared`。验证通过后先用 runner `state --to prepared` 记录 gate 证据（verify 结果 head、三个版本、dispatch mode、worker transport），再进入共享生命周期的 `prepared`、创建 Worker Record，并使用批准的 worker transport 和 dispatch mode 派发。实际 dispatch mode 与 gate record 不一致时立即转为 `blocked`，原因固定为 `dispatch_mode_mismatch` 并用 runner `state --to blocked` 记录；保留现场且不得进入 `dispatched`、`authorized` 或 `running`。

## 原子授权与派发

Claude Code 使用 `Authorization mode: atomic`，避免 worker 在 handshake 后停下并等待一条普通用户消息。

1. Coordinator 从已通过的 gate record 取得 `Plan version`、`Context version`、`Task version`、`Task ID` 与最新环境验证证据，并迁移为 `prepared`。
2. Coordinator 在初始 Execution Packet 中直接写入完整 `Authorization Evidence`，包含可复核的 `Environment verification` 和 `Write permission: granted`。
3. Coordinator 使用 `Agent(dev-with-tdd)` 派发一个只服务该 Task ID 的命名 worker，把返回 handle 或前台调用标识写入 Worker Record，并先用 runner `state --to dispatched --worker handle=...,transport=...` 记录，再执行派发。
4. 实际调用必须符合 gate record：`L1`、`L2` 或单 worker 一律以前台 `Agent(dev-with-tdd)` 运行。若宿主实际建立后台任务，即使请求参数看似正确，也以 `dispatch_mode_mismatch` 阻断。
5. worker 校验 packet 并返回版本化 handshake 后，Coordinator 先用 runner `state --to authorized` 记录，再迁移为 `authorized`；worker 随后进入 `running` 并直接实现（进入前用 runner `state --to running` 记录），不等待第二次 Coordinator 消息或用户输入。

初始 packet 的授权证据缺失、版本不一致、Git/workspace 证据过期或写入许可未明确 granted 时不得派发；状态转为 `context-gap` 或 `blocked`。原子授权不减少校验，只把完整校验结果绑定到首次派发。

## 串行完成与自动审查

串行 packet 固定使用 `Dispatch mode: foreground` 和 `Completion mode: foreground Agent result`。Coordinator 保持当前流程，直到前台 Agent 的 returned result 包含可认证的结构化 handoff。

收到结果后必须：

1. 核对 custom agent、Task ID 和三个版本；
2. 先用 runner `state --to handoff-received` 记录，再把 Worker Record 迁移为 `handoff-received`；
3. 先用 runner `state --to reviewing` 记录，再立即进入 `reviewing` 并独立检查实际 diff 与可复现验证；
4. 根据审查结果进入 `accepted`、`rework`、`context-gap` 或 `blocked`；每个迁移同样先用 runner `state` 记录。

Coordinator 不得在 Agent 返回后正常结束或等待普通用户消息来唤醒审查。结果为空、来源不确定、会话中断或无法认证最终 handoff 时转为 `blocked` 并保留现场。需要 rework 时通过同一命名 worker 续发窄反馈；worker handle 已失效时转为 `blocked`。

## L3 并行与结果聚合

Claude Code 同时最多 3 个后台 Agent。只有已批准的 `L3` background-aggregate packet，且计划审批前已经取得结果聚合能力证据，并在计划和 Runtime Context 中明确选择 `Dispatch mode: background-aggregate` 时才可后台并行。`L1`、`L2` 或单 worker 不得后台运行。

后台完成必须依赖宿主提供的 `host completion notification` 唤醒 Coordinator，并通过宿主 `result aggregation` 收齐和认证全部 handoff。Coordinator 保存每个后台 Agent 的 handle；每个 handoff 到达后立即进入该 packet 的 review，同时继续跟踪其他 worker。结果聚合能力没有在计划审批前证明时，计划本身必须选择前台串行。

禁止 busy polling。不得用 shell 查询、目录列表或紧密循环轮询后台状态，也不得把固定间隔的重复检查包装成等待机制；宿主 completion notification 或 result aggregation 不可用时必须 `blocked`。

不得在批准后把串行静默改为并行，或反向改变已批准的 Git mode。能力变化若会改变 dispatch 或 Git mode，必须重新规划并使旧批准失效。

## 强制层（可选安装）

`--harden-claude` 向每个已存在的 Claude 平台根目录的 `settings.json` 合并本 bundle 的 hooks 条目；`--unharden-claude` 精确移除。Hook 脚本随 skill 分发于 `${SKILL_ROOT}/scripts/hooks/`，安装器只负责接线 settings。

### 规则

1. **状态文件保护**：`.tmp/<task-id>/state.json` 只能由 bundled runner `state` 子命令写入；主会话或 worker 的直接写入一律拒绝（`state_file_protection`）。
2. **业务写边界**：任务处于 `authorized`/`running`/`rework` 时，worker（`agent_type = dev-with-tdd`）只允许写其 packet 的 `Allowed write paths`（目录前缀匹配），越界拒绝（`worker_write_outside_packet`）；主线程在任务结束前写业务路径一律拒绝（`coordinator_direct_write`），任务工作区 `.tmp/<task-id>/` 始终放行。
3. **Git 所有权**：状态性 git 命令（commit/push/fetch/pull/merge/rebase/reset/checkout/stash/clean/...）必须经 bundled runner 调用，直接执行拒绝（`git_owner_violation`）；只读子命令、`-C` 指向其他仓库与 runner 调用放行。
4. **派发门**：`Agent(dev-with-tdd)` 只在 state.json 为 `prepared` 且 `gate.status = passed`（或 `context-gap`/`rework`）时放行，否则拒绝（`dispatch_mode_mismatch`）。该规则依赖对 Agent 工具调用的正向识别，宿主某些版本上可能不触发（见下述残余限制），协议层 gate 始终兜底。
5. **非法终止警告**：Stop hook 在任务处于 `dispatched`/`running`/`handoff-received`/`reviewing` 时通过 additionalContext 续接对话要求继续审查；`approved`/`prepared` 且未派发时提示遗弃。每个 lifecycle 值只警告一次（sidecar `.stop-warned` 记录），fail-soft，用户仍可随时退出。

### 诚实边界

强制层只机械强制**顺序、路径与所有权边界**：什么时候可以写、写哪里、谁可以写、什么时候必须继续。它不验证 Analysis Brief 或 Execution Packet 的**内容质量**——计划是否完整、验收标准是否可测、review 是否真正独立，仍是 skill 契约与 Coordinator 复核的职责。Bash 写意图检测是启发式（第一防线）；确定性兜底始终是 gate 的 `verify --require-clean`（检测）与 runner 显式路径 `commit`（闭合）。

### 安装与卸载

- `./install.sh --harden-claude` / `./install.sh --unharden-claude`；两者互斥。
- 至少一个 `.claude`、`.claudeD`、`.claudeP` 根目录存在才执行；`.hermes` 与命名 profile 永不被触碰。
- settings.json 缺失时新建；存在时必须为严格 JSON（JSONC 注释拒绝且文件不动）；合并保留其他键、幂等；`--unharden-claude` 只删除 command 前缀位于本 bundle hooks 目录的条目，永不删除 settings 文件。
- 重装 skill（delete-then-copy）不改变 settings 接线（hook 路径不变）；卸载后需要新会话生效。
- Claude Code 低于 2.1.214 时安装器输出警告：subagent 工具调用的 `agent_id`/`agent_type` 标识与相关 hook 语义依赖较新版本，旧版本上强制不完整。

### 残余限制

`disableAllHooks` 设置与 `--dangerously-skip-permissions` 可绕过本强制层——它们是护栏而非安全边界；hook deny 在 bypass 模式下仍生效。`matcher: "Agent"` 的 hook 在部分宿主版本上可能不触发父线程派发事件（已知 issue），派发门按尽力而为设计，失败回落到协议层 gate。`git -C <其他仓库>` 明确越界放行。hook 每次 Write/Edit/Bash/Agent 调用约 50–100ms 的 python3 启动开销。

## 可见性与安装边界

- `plan-dev-tasks` 和 `dev-with-tdd` 使用仓库 `adapters/claude-code/agents/` 下的命名 custom agent definitions；安装到已存在的 Claude Code 平台根后，可在新会话或重启后的 `/agents` 中发现。
- `plan-dev-tasks` 保持用户开发请求的唯一入口与主会话 Coordinator；`dev-with-tdd` 只作为内部实现 worker。
- 安装只添加 definitions 与链接，默认不修改默认 agent、工具权限或全局配置；仅当显式传入 `--harden-claude` 时，才向已存在的 Claude 平台根目录的 `settings.json` 合并本 bundle 的 hooks 条目（保留其他键、可重复执行，`--unharden-claude` 精确移除）。
- Claude Code definitions 只属于 Claude Code，不复制到其他平台。
