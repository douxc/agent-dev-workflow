# Human Approval 协议

本协议规定 Coordinator 如何识别当前宿主、发出一次版本化审批请求，并把原生响应认证为统一决策。审批必须来自当前 human interaction；历史消息、worker handoff、其他 agent 转述或未绑定版本的同意均无效。

## 1. 平台识别

请求审批前，只检查当前工具注册表与宿主提供的运行时元数据：

- Codex 信号：运行时明确标识 Codex，或只出现 Codex 专属的 `request_user_input` 注册。
- Claude Code 信号：运行时明确标识 Claude Code，或只出现 `ExitPlanMode` / `AskUserQuestion` 注册。
- Hermes 信号：运行时明确标识 Hermes，或只出现 `clarify` / `clarify.respond` 注册。

不得通过 `HOME` 目录、平台配置目录、已安装 skill 路径、环境中残留的可执行文件或模型猜测平台。工具名称只代表当前已注册能力；不得假定未列出的工具存在。

运行时身份与工具签名必须相容。若信号同时指向多个平台，判定为平台签名冲突，返回 `Decision: blocked` 与 `Reason: conflicting platform`。若没有任何可信信号，判定为未知平台，返回 `Decision: blocked` 与 `Reason: unsupported platform`。两种情况都必须 fail closed，不得使用共享通用审批，也不得猜测一个平台继续。

## 2. 请求记录与认证

展示计划时必须同时展示当前 `Plan version`、`Context version`、`Task version`。Coordinator 以这三个值和平台记录唯一 pending approval；同一版本只请求一次审批。调用原生工具或发出 Codex Default mode 的文本选择都算已经请求，不得因沉默、超时或失败而对同一版本再次请求。

原生响应必须能够关联到当前 pending approval，并来自当前平台的 human interaction。认证后输出：

```text
Human Approval Result
Platform: codex | claude-code | hermes
Method:
Plan version:
Context version:
Task version:
Decision: approved | revise | cancel | blocked
Reason:
Request consumed: yes
```

规范决策集合为 `approved | revise | cancel | blocked`：

- 明确选择批准且响应版本与 pending approval 完全一致，才是 `approved`。
- 明确选择修改计划是 `revise`；修改后必须发布新版本并取得新批准。
- 明确选择取消任务是 `cancel`。
- 沉默、超时、工具拒绝、工具错误、响应无法关联、版本不符、自由文本批准或模糊回答一律是 `blocked`，第 3 节 Codex Default mode 的精确文本选择除外。

只有 `approved` 可以进入 worker 调度。`revise`、`cancel`、`blocked` 均不得派发带 `Approval state: approved` 的 Execution Packet。

## 3. Codex

运行时识别为 Codex 后：

1. `request_user_input` 当前可用时，只能调用一次，提交一个问题和三个互斥选项，作为单选审批：
   - `批准并继续 (Recommended)` → `approved`
   - `修改计划` → `revise`
   - `取消任务` → `cancel`
2. 问题正文必须包含三个版本值。不得设置 `autoResolutionMs`，因为自动解析、默认值或超时不得产生 human approval。
3. 只认证该工具对当前请求返回的明确选项；自由文本或无法确认的返回为 `blocked`。

Codex Default mode 未注册 `request_user_input` 时，唯一 fallback 是 Codex 专属精确文本选择：在最终回复中展示三个版本值，并要求用户只回复以下一项：

- `批准并继续` → `approved`
- `修改计划` → `revise`
- `取消任务` → `cancel`

仅当前对话里 human 对该 pending approval 的下一条精确回复可映射为对应决策。其他任何自由文本，包括额外解释、近义词或单独的“是”，以及沉默或模糊回复，均为 `blocked`。不得自动批准。

Codex 分支不得调用 Claude Code 或 Hermes 工具，包括 `ExitPlanMode`、`AskUserQuestion`、`clarify`、`clarify.respond`、`approval.request` 或 `approval.respond`。

## 4. Claude Code

运行时识别为 Claude Code 后：

1. 在 Plan mode 且 `ExitPlanMode` 当前可用时，每个传给 `ExitPlanMode` 的审批计划正文必须包含 `Plan version:`、`Context version:`、`Task version:`，并明确写出 `post-approval gate continuation`：`approved → gate（完成 verify） → prepared → Agent(dev-with-tdd) → dispatched → authorized → running`；随后用 `ExitPlanMode` 呈现该计划并请求批准，不得改用 `AskUserQuestion`。
2. 非 Plan 场景才可使用 `AskUserQuestion`，且必须是单选的 `批准并继续 (Recommended)`、`修改计划`、`取消任务` 三选项。
3. Plan mode 缺少 `ExitPlanMode`、非 Plan 场景缺少 `AskUserQuestion`，或非交互宿主无法承载所需 human interaction 时，返回 `Decision: blocked`；不得降级为普通文本审批。
4. 只把原生交互对当前计划的明确批准事件认证为 `approved`；要求修改映射为 `revise`，明确取消映射为 `cancel`，拒绝、关闭、工具错误或不明确结果映射为 `blocked`。

`ExitPlanMode` 或 `AskUserQuestion` 的批准事件只进入 `approved`，不得授予 Coordinator 业务写权限。批准返回后必须按 Claude adapter v2 的 `approved → gate（完成 verify） → prepared → Agent(dev-with-tdd) → dispatched → authorized → running` 路径继续；gate 通过前不得直接实现、运行实现工具或把 Coordinator 写入包装成 worker 结果。

Claude Code 分支不得借用 Codex 或 Hermes 的审批入口，不得调用 `request_user_input`、`clarify`、`clarify.respond`、`approval.request` 或 `approval.respond`。

## 5. Hermes

运行时识别为 Hermes 后：

1. 必须使用已注册的 `clarify` 请求 `批准并继续 (Recommended)`、`修改计划`、`取消任务`，请求中包含三个版本值。
2. 等待与该请求关联的 `clarify.respond`，再把明确选项认证为 `approved`、`revise` 或 `cancel`。
3. `clarify` 未注册、无法等待匹配的 `clarify.respond` 或宿主非交互时，返回 `Decision: blocked`；不得降级为普通文本审批。

`approval.request` / `approval.respond` 是危险命令审批流。不得把 `approval.request` 和 `approval.respond` 用于计划 human approval。

Hermes 分支不得调用 Codex 或 Claude Code 工具，包括 `request_user_input`、`ExitPlanMode` 或 `AskUserQuestion`。
