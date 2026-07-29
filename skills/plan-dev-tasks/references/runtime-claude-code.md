# Claude Code Runtime Adapter

本文件只把共享 Runtime Adapter 契约映射到 Claude Code 原生 custom agent 能力。加载条件是 `Runtime Context` 已认证为 Claude Code；共享生命周期、Worker Record 和审查规则仍以 [runtime-adapters.md](runtime-adapters.md) 为准。

```text
Runtime Context:
  Platform: claude-code
  Adapter version: 1
  Worker transport: Agent(dev-with-tdd)
  Dispatch mode: foreground | background-aggregate
  Authorization mode: atomic
  Completion mode: foreground Agent result | explicit background result aggregation
  Capability evidence: authenticated Claude Code runtime metadata, registered Agent tool, named dev-with-tdd custom agent, and proven result return path
```

## Human approval 与能力选择

计划审批沿用 [human-approval.md](human-approval.md) 的 Claude Code 分支：Plan mode 使用 `ExitPlanMode`，非 Plan 场景使用 `AskUserQuestion`。审批能力、custom agent 可见性和结果回传能力必须分别验证。

Coordinator 派发前必须取得最小能力证据：

- 当前宿主的认证运行时元数据指向 Claude Code，且没有冲突的平台信号；
- `Agent` 工具当前可用，且名为 `dev-with-tdd` 的 custom agent 已加载；
- 串行任务能以前台 Agent 返回的 returned result 恢复当前 Coordinator；
- 并行任务还必须证明每个后台 Agent 的结果可被显式聚合并重新注入当前 Coordinator。

必要能力缺失、custom agent 未加载、返回来源不确定或平台信号冲突时 fail closed。不得用普通 skill 加载动作冒充独立 worker transport，也不得在共享主上下文直接实现后伪造 handoff。

## 原子授权与派发

Claude Code 使用 `Authorization mode: atomic`，避免 worker 在 handshake 后停下并等待一条普通用户消息。

1. Coordinator 在派发前核对 `Plan version`、`Context version`、`Task version` 和 `Task ID`。
2. Git 项目通过 runner `verify` 核对实际 Worktree、Task branch、Expected HEAD 与 Base SHA；非 Git 项目完成 workspace 边界验证。
3. Coordinator 创建 Coordinator-only Worker Record，并在初始 Execution Packet 中直接写入完整 `Authorization Evidence`，包含可复核的 `Environment verification` 和 `Write permission: granted`。
4. Coordinator 使用 `Agent(dev-with-tdd)` 派发一个只服务该 Task ID 的命名 worker，并把返回 handle 或前台调用标识写入 Worker Record。
5. worker 校验 packet，返回版本化 handshake 后直接进入实现，不等待第二次 Coordinator 消息或用户输入。

初始 packet 的授权证据为 pending、版本不一致、Git/workspace 证据过期或写入许可未明确 granted 时不得派发；状态转为 `context-gap` 或 `blocked`。原子授权不减少校验，只把完整校验结果绑定到首次派发。

## 串行完成与自动审查

串行 packet 固定使用 `Dispatch mode: foreground` 和 `Completion mode: foreground Agent result`。Coordinator 保持当前流程，直到前台 Agent 的 returned result 包含可认证的结构化 handoff。

收到结果后必须：

1. 核对 custom agent、Task ID 和三个版本；
2. 把 Worker Record 迁移为 `handoff-received`；
3. 立即进入 `reviewing` 并独立检查实际 diff 与可复现验证；
4. 根据审查结果进入 `accepted`、`rework`、`context-gap` 或 `blocked`。

Coordinator 不得在 Agent 返回后正常结束或等待普通用户消息来唤醒审查。结果为空、来源不确定、会话中断或无法认证最终 handoff 时转为 `blocked` 并保留现场。

## L3 并行与结果聚合

Claude Code 同时最多 3 个后台 Agent。L3 只有在计划审批前已经取得结果聚合能力证据，并在计划和 Runtime Context 中明确选择 `Dispatch mode: background-aggregate` 时才可并行。

Coordinator 必须保存每个后台 Agent 的 handle，显式等待并聚合全部 handoff；每个 handoff 到达后立即进入该 packet 的 review，同时继续跟踪其他 worker。结果聚合能力没有在计划审批前证明时，计划本身必须选择串行。

不得在批准后把串行静默改为并行，或反向改变已批准的 Git mode。能力变化若会改变 dispatch 或 Git mode，必须重新规划并使旧批准失效。

## 可见性与安装边界

- `plan-dev-tasks` 和 `dev-with-tdd` 使用仓库 `adapters/claude-code/agents/` 下的命名 custom agent definitions；安装到已存在的 Claude Code 平台根后，可在新会话或重启后的 `/agents` 中发现。
- `plan-dev-tasks` 保持用户开发请求的唯一入口与主会话 Coordinator；`dev-with-tdd` 只作为内部实现 worker。
- 安装只添加 definitions 与链接，不修改默认 agent、工具权限或全局配置。
- Claude Code definitions 只属于 Claude Code，不复制到其他平台。
