# Human Approval 契约

本契约规定 Coordinator 如何发出一次版本化审批请求，并把原生响应认证为统一决策。审批必须来自当前 human interaction；历史消息、worker handoff、其他 agent 转述或未绑定版本的同意均无效。平台具体审批入口与交互由匹配的 platform flow 定义。

## 1. 一次版本化审批

展示计划时必须同时展示当前 `Plan version`、`Context version`、`Task version`。Coordinator 以这三个值唯一记录 pending approval；同一版本只请求一次审批。调用匹配平台 flow 规定的原生审批入口即算已经请求，不得因沉默、超时或失败而对同一版本再次请求。

审批选择的规范文案为 `批准并继续 (Recommended)`、`修改计划`、`取消任务`。平台 flow 必须以单选方式呈现这三项，并在请求正文中包含三个版本值。

## 2. 决策认证

原生响应必须能够关联到当前 pending approval，并来自当前平台的 human interaction。认证后输出：

```text
Human Approval Result
Platform: claude-code | hermes
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
- 沉默、超时、工具拒绝、工具错误、响应无法关联、版本不符、自由文本批准或模糊回答一律是 `blocked`。不得自动批准，也不得把任何自由文本映射为决策。

只有 `approved` 可以进入 worker 调度。`revise`、`cancel`、`blocked` 均不得派发带 `Approval state: approved` 的 Execution Packet。

`approved` 只表示当前版本计划获准进入匹配平台 flow 定义的派发流程，不授予 Coordinator 业务写权限。批准返回后必须先执行该 flow 的 post-approval dispatch gate，通过后才进入准备与派发；gate 通过前不得直接实现、运行实现工具或把 Coordinator 写入包装成 worker 结果。

## 3. 平台审批入口

平台具体审批入口与交互由匹配的 platform flow 定义，Coordinator 不得跨平台借用审批入口：

- Claude Code：见 [claude-code-flow.md](claude-code-flow.md)。Plan mode 使用 `ExitPlanMode` 呈现审批计划（正文含三个版本与 post-approval gate continuation），非 Plan 场景使用 `AskUserQuestion` 单选三选项。
- Hermes：见 [hermes-flow.md](hermes-flow.md)。使用 `clarify` 请求三选项并等待关联的 `clarify.respond`；不得把 `approval.request` / `approval.respond` 用于计划审批。

宿主未注册匹配平台 flow 所需的原生审批工具、平台信号冲突或非交互宿主无法承载所需 human interaction 时，返回 `Decision: blocked`；不得降级为普通文本审批，也不得猜测一个平台继续。
