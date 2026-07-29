# Hermes Runtime Adapter

本文件只把共享 Runtime Adapter 契约映射到 Hermes 原生 delegation 能力。加载条件是 `Runtime Context` 已认证为 Hermes；共享生命周期、Worker Record 和审查规则仍以 [runtime-adapters.md](runtime-adapters.md) 为准。

```text
Runtime Context:
  Platform: hermes
  Adapter version: 1
  Worker transport: delegate_task
  Dispatch mode: foreground | background-aggregate
  Authorization mode: atomic
  Completion mode: result reinjection | synchronous delegate result
  Capability evidence: authenticated Hermes runtime metadata, actually registered delegate_task, and an authenticated delegate result path
```

## Human approval 与能力选择

计划审批沿用 [human-approval.md](human-approval.md) 的 Hermes 分支：Coordinator 使用 `clarify` 完成 human approval，审批决定必须在派发前认证并绑定当前计划版本。审批能力、delegation 能力和结果回传能力必须分别验证。

Coordinator 派发前必须取得最小能力证据：

- 当前宿主的认证运行时元数据指向 Hermes，且没有冲突的平台信号；
- 当前会话已经 actually registered `delegate_task`，并能取得可绑定到 child identity 的返回标识；
- 支持会话结果投递的宿主能通过 result reinjection 恢复同一个 Coordinator 状态机；
- stateless 宿主能在当前调用中取得 synchronous delegate result；
- 并行计划还必须证明能聚合一个 batch 内的全部结果，并认证每个结果的 child identity 和 Task ID。

必要能力缺失、delegation 未认证、结果路径不确定或平台信号冲突时 fail closed，状态转为 `blocked`。不得用普通 skill 调用或主上下文实现冒充 child，也不得把来源不明的文本包装成 delegate handoff。

## 原子授权与派发

Hermes 使用 `Authorization mode: atomic`，因为 child 不得调用 `clarify`，也不能把审批责任转交给临时运行实例。

1. Coordinator 在派发前核对 `Plan version`、`Context version`、`Task version` 和 `Task ID`。
2. Git 项目通过 runner `verify` 核对实际 Worktree、Task branch、Expected HEAD 与 Base SHA；非 Git 项目完成 workspace 边界验证。
3. Coordinator 创建 Coordinator-only Worker Record，并在初始 Execution Packet 中直接写入完整 `Authorization Evidence`，包含可复核的 `Environment verification` 和 `Write permission: granted`。
4. Coordinator 调用原生 delegation transport，派发一个只服务该 Task ID 的 child，并把返回的 child identity 写入 Worker Record。
5. child 验证 packet 和完整授权证据，产生版本化 handshake 后直接进入实现，不等待第二次 Coordinator 消息或普通用户输入。

初始 packet 的授权证据为 pending、版本不一致、环境证据过期或写入许可未明确 granted 时不得派发；状态转为 `context-gap` 或 `blocked`。原子授权不减少校验，只把已经完成的批准和环境验证绑定到首次派发。child 不得调用 `clarify`，也不得自行补全、更新或重新申请授权。

## 完成回传与自动审查

Hermes 支持两种经过能力验证的完成路径：

- 会话宿主支持结果投递时，delegate 完成结果通过 result reinjection 重新注入当前 Coordinator，并恢复原 Worker Record 与生命周期；
- stateless 宿主没有异步投递能力时，当前 delegation 调用必须同步返回 synchronous delegate result，Coordinator 在同一流程中继续。

无论使用哪条路径，Coordinator 收到结果后都必须：

1. 核对 child identity、Task ID、`Plan version`、`Context version` 和 `Task version`；
2. 将可认证的结构化 handoff 写入 Worker Record，并迁移为 `handoff-received`；
3. 立即从 `handoff-received` 进入 `reviewing`，独立检查实际 diff 与可复现验证；
4. 根据审查结果进入 `accepted`、`rework`、`context-gap` 或 `blocked`。

Coordinator 不得等待普通用户消息来唤醒审查。结果为空、来源不确定、child identity 丢失、session interruption、process restart 或 child/result 状态不确定时，必须转为 `blocked` 并保留现场、Worker Record 和已有证据；不得猜测成功、重复派发或清理 worktree。

## 并发与聚合

Hermes 单次 batch 最多 3 个 child。只有计划审批前已经证明 batch 结果聚合与 Coordinator 恢复能力，并选择 `Dispatch mode: background-aggregate` 时，才可并行派发。

Coordinator 为每个 child 维护独立 Worker Record，认证并聚合全部结果；每个 handoff 到达后立即审查对应 packet，同时继续跟踪其他 child。只有全部结果均已认证并完成相应审查后，聚合阶段才可结束。聚合能力未证明时必须在计划阶段选择 `foreground`，不得在批准后静默改变 dispatch 或 Git mode。

## 可见性与安装边界

- 两个共享 skill 继续通过 Hermes 的 `/skills` 发现。
- delegate children 是 temporary runtime instances，不是持久命名 agent definitions。
- Hermes 不使用 `.hermes/agents`；安装器不得创建该目录、复制其他平台的 agent definitions 或修改默认 agent、权限和全局配置。
- skill 可见性不是 child transport，不能代替已认证的 delegation 能力。
