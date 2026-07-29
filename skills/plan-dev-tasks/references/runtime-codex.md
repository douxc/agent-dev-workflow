# Codex Runtime Adapter

本文件只把共享 Runtime Adapter 契约映射到 Codex 原生 collaboration 能力。加载条件是 `Runtime Context` 已认证为 Codex；共享生命周期、Worker Record 和审查规则仍以 [runtime-adapters.md](runtime-adapters.md) 为准。

```text
Runtime Context:
  Platform: codex
  Adapter version: 1
  Worker transport: spawn_agent + same-worker message continuation
  Dispatch mode: foreground | background-aggregate
  Authorization mode: two-phase
  Completion mode: wait_agent/mailbox final handoff
  Capability evidence: authenticated Codex runtime metadata plus actually registered collaboration tools
```

## 能力选择与 fail closed

Coordinator 必须在派发前根据当前工具注册表取得最小 `Capability evidence`，并确认：

- 当前宿主的认证运行时元数据指向 Codex，且没有冲突的平台信号；
- 已 actually registered `spawn_agent`；
- 已 actually registered 至少一种可绑定同一 worker handle 的续发能力：worker 运行时使用 `send_message`，worker 空闲时可用 `followup_task` 触发续跑；
- 已 actually registered `wait_agent`，并且 agent mailbox 能把 worker 的结构化最终 handoff 返回给当前 Coordinator；
- 并行计划还必须证明能分别保留全部 worker handle、聚合全部 handoff 并恢复 Coordinator。

任一必要能力缺失、handle 不能稳定关联同一 worker、mailbox 结果来源不确定或平台信号冲突时 fail closed，状态转为 `blocked`。不得用普通主上下文冒充 worker，也不得把主上下文中的直接实现包装成伪 handoff。

Codex 的 human approval 继续遵循 [human-approval.md](human-approval.md)：可用时使用 `request_user_input`；Default mode 只能使用该契约定义的 Codex 专属精确文本 fallback。审批能力不等于 collaboration 能力，两类证据必须分别验证。

## 派发与两阶段授权

1. Coordinator 完成 Git runner `verify`（非 Git 项目完成 workspace 边界验证），创建 Coordinator-only Worker Record，并把状态设为 `prepared`。
2. 使用 `spawn_agent` 创建只服务一个 Task ID 的 worker，把 worker handle 写入 Worker Record，然后迁移为 `dispatched`。
3. 初始 packet 的 `Authorization mode: two-phase`，`Environment verification` 与 `Write permission` 均为 `pending`。worker 此时只读并返回版本化 handshake，不得修改文件。
4. Coordinator 必须核对 handshake 的 `Plan version`、`Context version`、`Task version`、`Task ID`，并再次核对实际 `Worktree`、`Task branch`、`Expected HEAD`、`Base SHA` 与 runner 证据。
5. 只有全部匹配时，Coordinator 才通过同一 worker handle 使用已注册的 `send_message` 或 `followup_task` 续发完整 `Authorization Evidence`，其中 `Write permission: granted`。Worker Record 迁移为 `authorized`，worker 开始实现时迁移为 `running`。

版本、Git 上下文、worker handle 或授权证据不匹配时不得写入；状态转为 `context-gap` 或 `blocked` 并保留现场。Coordinator 不得另建 worker 来绕过失败的 handshake。

## 完成、续跑与自动审查

授权后 Coordinator 必须持续使用 `wait_agent` 读取 agent mailbox，直到对应 worker handle 返回可认证的结构化最终 handoff。等待期间暂时没有消息只是 `running`，不是完成或暂停理由。

收到最终 handoff 后必须：

1. 核对 worker handle、Task ID 和三个版本；
2. 把 Worker Record 从 `running` 迁移为 `handoff-received`；
3. 立即从 `handoff-received` 迁移为 `reviewing`，独立检查实际 diff 与可复现验证；
4. 根据审查结果进入 `accepted`、`rework`、`context-gap` 或 `blocked`。

Coordinator 在 `dispatched`、`running`、`handoff-received` 或 `reviewing` 不得正常结束，也不得等待普通用户消息来唤醒审查。需要 rework 时必须通过原 worker handle 续发同一 Task ID 的窄反馈；handle 已失效或结果不能认证时转为 `blocked`。

## 并发与聚合

Codex 同时最多 3 个 collaboration workers。只有 Runtime Context 在审批前已经选择 `Dispatch mode: background-aggregate`，并且能力证据证明可跟踪所有 handle、收齐全部 handoff 时，才可并行派发。

并行时 Coordinator 为每个 worker 维护独立 Worker Record，通过 `wait_agent` 持续聚合全部 handoff；某个 worker 完成后立即审查其 packet，同时继续跟踪其他运行中的 worker。Coordinator 只有在全部 handoff 已认证并完成相应审查后，才可结束聚合阶段。聚合能力未证明时必须在计划阶段选择 `foreground`，不得在批准后静默更改 Git mode。

## 可见性与安装边界

- 运行中的协作实例由 Codex 原生 runtime agent tree 展示。
- skill 的 UI 发现信息继续来自各 skill 内的 `agents/openai.yaml`。
- Codex 不需要 `.codex/agents` 文件型定义；安装器不得为此创建目录或链接。
- collaboration worker 是临时运行实例，skill metadata 不是 worker transport，也不能代替能力证据。
