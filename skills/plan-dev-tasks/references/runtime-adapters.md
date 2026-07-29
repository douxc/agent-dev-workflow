# Runtime Adapter 契约

本契约把平台无关的开发生命周期与宿主平台的审批、worker transport、结果回传和可见性机制分离。共享 core 只维护状态和证据，不直接调用任何平台专属工具。

## Runtime Context

每个 Execution Packet 必须包含由 Coordinator 根据当前运行时证据生成的上下文：

```text
Runtime Context:
  Platform: codex | claude-code | hermes
  Adapter version:
  Worker transport:
  Dispatch mode: foreground | background-aggregate
  Authorization mode: two-phase | atomic
  Completion mode:
  Capability evidence:
```

- `Platform` 必须由当前工具注册表和运行时元数据共同证明；不得通过用户目录、路径命名或模型猜测。
- `Adapter version` 标识已加载的平台 adapter 契约版本。
- `Worker transport` 和 `Completion mode` 必须描述已验证可用的原生 worker 与结果回传能力。
- `background-aggregate` 只有在审批前已经证明可跟踪全部 worker、收齐 handoff 并恢复 Coordinator 时可用；否则计划必须选择 `foreground`。
- `Capability evidence` 只记录最小、可复核的能力证据，不记录秘密、完整工具清单或 transcript。

平台信号冲突、未知平台、adapter 缺失、声明能力与实际注册能力不一致或结果回传不确定时 fail closed。只加载与已识别 `Platform` 精确匹配的一个 Runtime Adapter；不得跨 adapter fallback，也不得在共享主上下文中冒充缺失的 worker。

## Adapter 路由

平台识别和能力核验完成后，仅按 `Platform` 加载下列匹配项：

- `codex`：[runtime-codex.md](runtime-codex.md)
- `claude-code`：[runtime-claude-code.md](runtime-claude-code.md)

列表中没有匹配项时视为 adapter 缺失并 fail closed；不得选择相近平台或继续派发。

## Worker Record

Coordinator 为每个已派发 packet 维护一个 **Coordinator-only Worker Record**：

```text
Worker Record:
  Task ID:
  Platform:
  Adapter version:
  worker handle:
  Lifecycle state:
  Dispatch evidence:
  Authorization evidence:
  Completion evidence:
  Final handoff:
```

Worker Record 不得传给 worker，也不得放进 Execution Packet。它用于关联平台 worker handle、状态迁移和最终 handoff；worker 只能看到完成自身任务所需的 `Runtime Context` 和授权证据，不能写入或决定 Worker Record。

## 统一生命周期

每个 packet 严格按以下状态迁移：

```text
approved
→ prepared
→ dispatched
→ authorized
→ running
→ handoff-received
→ reviewing
→ accepted | rework | context-gap | blocked
→ committed
→ finalized
```

- `approved → prepared`：审批版本有效，执行环境和 Runtime Context 已验证。
- `prepared → dispatched`：匹配平台的 adapter 已创建或调用一个 worker，并建立 Worker Record。
- `dispatched → authorized`：`two-phase` 已校验 handshake 并续发写入许可；`atomic` 已在派发前把完整授权随 packet 交付。
- `authorized → running`：worker 开始受控发现和实现。
- `running → handoff-received`：Coordinator 通过声明的 `Completion mode` 收到结构化 handoff，并核对 Task ID 与三个版本。
- `handoff-received → reviewing`：Coordinator 必须立即进入 `reviewing`，独立检查实际 diff 和可复现证据，不得等待普通用户消息唤醒。
- `reviewing → accepted | rework | context-gap | blocked`：只由 Coordinator 作出审查结论。
- `accepted → committed → finalized`：按 Git、地图、发布和清理契约持久化并结束；非 Git 项目的 `committed` 表示已按批准方式持久化。

`rework` 恢复同一 Task ID 的 worker 并重新进入适用的授权/运行状态；`context-gap` 和 `blocked` 保留现场并按主技能的状态规则处理。

Coordinator 在 `dispatched`、`running`、`handoff-received` 或 `reviewing` 时不得正常结束。平台回传暂时没有新消息不等于任务完成；必须按 adapter 的 completion 机制继续等待或恢复。worker handle 丢失、会话中断或最终 handoff 无法认证时转为 `blocked`，不得假定成功。

## 授权模式

两个模式共用以下最小证据形状：

```text
Authorization Evidence:
  Plan version:
  Context version:
  Task version:
  Task ID:
  Environment verification: Git runner verify evidence | non-Git workspace boundary evidence
  Write permission: granted
```

- `two-phase`：先派发只含继承审批和只读上下文的 packet；worker 返回版本化 handshake 后停止。Coordinator 核对 Task ID、三个版本、执行环境证据和 Git verify，再通过同一 worker handle 明确授予写入许可。
- `atomic`：Coordinator 在派发前完成相同核对，把 Task ID、三个版本、Git runner verify 结果（非 Git 项目为 workspace 边界验证证据）和明确写入许可作为授权证据随 packet 一次性交付。worker 验证后可在 handshake 后直接运行，不等待第二次消息。

`two-phase` 初始 packet 的 environment 与 permission 值为 `pending`，完整 `Authorization Evidence` 只能在 handshake 通过后通过同一 worker handle 续发；`atomic` 的初始 packet 必须直接包含完整证据。任一模式都不得让 worker 自行补全、推断或伪造授权证据。授权证据缺失、过期、版本不一致或不能绑定当前 worker/worktree 时为 `context-gap` 或 `blocked`，不得写入。
