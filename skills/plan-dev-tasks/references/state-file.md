# 状态文件契约

本文件定义 Execution Packet 生命周期状态的可机器读取事实来源：`state.json`。它是强化层（Claude Code hooks）与审计的基础；平台无关，Claude Code 与 Hermes 共用同一文件与同一写入者规则。

## 1. 位置与所有权

状态文件固定为：

```text
${PROJECT_ROOT}/.tmp/<task-id>/state.json
```

与 `task-owner.json` 同目录，遵守 [task-workspace.md](task-workspace.md) 的 ownership 与清理规则：随任务目录一并清理，不单独保留。

**唯一写入者是 bundled runner**：只有 `scripts/git-workflow.sh` 的 `state` 子命令可以创建或修改 `state.json`。Coordinator 不得用文件编辑工具直接写 `state.json`，也不得要求 worker 读取或维护它。`state.json` 是生命周期状态、三个版本号与 gate 证据的单一事实来源（single source of truth）。

## 2. Schema v1

```json
{
  "schema_version": 1,
  "task_id": "string",
  "project_root": "canonical absolute",
  "task_directory": "canonical absolute",
  "created_at": "ISO8601",
  "lifecycle": "approved | prepared | dispatched | authorized | running | handoff-received | reviewing | accepted | rework | context-gap | blocked | committed | finalized",
  "gate": {
    "status": "pending | passed | failed | not-applicable",
    "blocked_reason": "none | coordinator_direct_write | dispatch_mode_mismatch | other",
    "approval_event": "string",
    "plan_version": "string",
    "context_version": "string",
    "task_version": "string",
    "dispatch_mode": "foreground | background-aggregate | unknown",
    "worker_transport": "string",
    "verify_result": "passed | failed | not-applicable",
    "head": "sha40 | not-applicable",
    "verified_at": "ISO8601 | null"
  },
  "versions": { "plan": "string", "context": "string", "task": "string" },
  "packets": [
    {
      "packet_id": "string",
      "lifecycle": "同 lifecycle 枚举",
      "task_branch": "string | null",
      "worktree": "string | null",
      "expected_head": "sha40 | null",
      "allowed_write_paths": ["root-relative"]
    }
  ],
  "worker": { "handle": "string | null", "transport": "string | null" },
  "transitions": [
    { "from": "none | 枚举", "to": "枚举", "at": "ISO8601", "evidence": "string" }
  ]
}
```

字段约束：

- 未知顶层键、未知嵌套键、枚举外取值一律拒绝（fail closed）。
- `versions` 与 `gate.*_version` 都非空；两者不一致时以 gate 版本为派发证据，不一致即拒绝。
- 版本字符串不得包含逗号或控制字符。
- `allowed_write_paths` 每项必须是项目相对路径，字符集限 `[A-Za-z0-9._/-]`，不得以 `/` 开头，不得含 `..`。
- `transitions` 按时间追加，只增不改；`blocked` 与 `finalized` 是终态，不得再有迁移。
- `packets[].lifecycle` 是信息字段，由 Coordinator 在 `--packet` 更新时显式维护（L3 中各 packet 独立迁移）；强制执行以任务 `lifecycle` 为准。

## 3. 合法迁移表

| from | to | 前置条件 |
|---|---|---|
| `approved` | `prepared` | `gate.status = passed` |
| `prepared` | `dispatched` | `worker.transport` 非空 |
| `dispatched` | `authorized` | 无 |
| `authorized` | `running` | 无 |
| `running` | `handoff-received` | 无 |
| `handoff-received` | `reviewing` | 无 |
| `reviewing` | `accepted` / `rework` / `context-gap` / `blocked` | `blocked` 要求 `gate.blocked_reason` 非空 |
| `accepted` | `committed` | 无 |
| `committed` | `finalized` | 无 |
| `rework` | `authorized` / `running` | 无 |
| `context-gap` | `prepared` / `blocked` | `blocked` 要求 `gate.blocked_reason` 非空 |
| `blocked` / `finalized` | — | 终态 |

`--init` 创建文件时 lifecycle 固定为 `approved`，gate 默认 `status: pending`，`blocked_reason: none`，packets 与 worker 为空。

## 4. runner 用法

```text
git-workflow.sh state --init --project-root R --task-id T \
    --versions plan=V1,context=V2,task=V3

git-workflow.sh state --to <lifecycle> --project-root R --task-id T \
    [--gate status=...,blocked_reason=...,approval_event=...,plan_version=...,context_version=...,task_version=...,dispatch_mode=...,worker_transport=...,verify_result=...,head=...] \
    [--worker handle=...,transport=...] \
    [--packet id=...,lifecycle=...,branch=...,worktree=...,expected_head=...,allowed_write_paths=...] \
    [--evidence "自由文本"]

git-workflow.sh state --show --project-root R --task-id T
```

- `--project-root` 只做 canonical 规范化，**不要求 Git 仓库**（区别于其他子命令），非 Git 工作区同样可用。
- `--init` 在文件已存在时报错（拒绝覆盖）；`--to`/`--show` 在文件缺失或损坏时报错（fail closed）。
- 迁移、gate 前置条件与字段一致性由 runner 内联校验；写入是原子的（临时文件 + rename）。
- `--to` 时 `--gate`/`--worker`/`--packet` 只更新提供的字段；`--packet` 按 `id` 定位，不存在则追加，存在则合并。
- 输出保持 runner 稳定的 `key<TAB>value` 约定：`task_id`、`lifecycle`、`gate_status`、`updated_at`（最近一次迁移时间）。

## 5. 与强化层的关系

Claude Code 加固宿主（可选安装，见 claude-code-flow.md 强制层）的 PreToolUse hooks 读取 `state.json` 判定放行/拦截：

- 无状态文件 → hooks 休眠，不干预；
- `approved`/`prepared`（gate 未通过）→ 拦截主会话对业务路径的写入，原因 `coordinator_direct_write`；
- 已派发（`authorized`/`running`）→ 只允许 worker 在其 packet 的 `allowed_write_paths` 内写入；
- 派发（Agent 工具）仅在 `prepared` 且 `gate.status = passed`（或 `context-gap`/`rework`）时放行，原因 `dispatch_mode_mismatch`。

Stop hook 依据 lifecycle 对非法终止（`dispatched`/`running`/`handoff-received`/`reviewing`）与未派发任务（`approved`/`prepared`）发出警告。

## 6. 诚实边界

状态文件与 hooks 只强制**顺序、路径与所有权边界**：什么时候可以写、写哪里、谁可以写、什么时候必须继续。它们不验证 Analysis Brief 或 Execution Packet 的**内容质量**——计划是否完整、验收标准是否可测、review 是否真的独立，仍是 skill 契约与 Coordinator 复核的职责。
