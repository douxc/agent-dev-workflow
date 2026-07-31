# Execution Packet 接口

每个 packet 只描述一个可独立执行和验证的 feature：

```text
Required skill: dev-with-tdd
Approval state: pending | approved
Plan version:
Context version:
Task version:
Task ID:
中文标题:
Task workspace:
Goal:
Acceptance criteria:
In scope:
Out of scope:
Dependencies:
Shared interfaces:
Allowed write paths:
Allowed discovery paths:
Forbidden paths:
Forbidden side effects:
Stop conditions:
Project Context:
  Source fingerprint:
  Relevant map entries:
  Applicable constraints:
  Local overrides:
  Verified source paths:
  Relevant tests:
  Code evidence:
Workspace Context:
  Baseline fingerprint:
  Relevant file fingerprints:
  Existing user changes:
Runtime Context:
  Platform: claude-code | hermes
  Platform flow: claude-code-flow.md | hermes-flow.md
  Worker transport:
  Dispatch mode: foreground | background-aggregate
  Authorization mode: atomic
  Completion mode:
  Capability evidence:
Authorization Evidence:
  Plan version:
  Context version:
  Task version:
  Task ID:
  Environment verification: Git runner verify evidence | non-Git workspace boundary evidence
  Write permission: granted
Git Context:
  Mode: local-only | serial | parallel
  Project root:
  Remote: none | remote name
  Default branch:
  Base SHA:
  Task branch:
  Worktree:
  Expected HEAD:
  Expected default tip: SHA | not-applicable
  Expected remote tip: absent | SHA | not-applicable
  Shared dependency paths: none | project-relative paths
  Shared dependency fingerprints: none | manifest/lockfile fingerprints
  Git owner: Coordinator
  Remote publish authorization: approved | denied
TDD classification: required | not required
TDD reason:
Red test plan:
Green implementation plan:
Focused verification:
Expanded verification:
Language check: passed
```

## 内容边界

- `Allowed write paths` 是硬写入边界；必须使用具体项目相对路径或不会意外扩大的窄 pattern。
- `Allowed discovery paths` 可包含目标文件、直接依赖、相关类型、测试、项目指令和局部注释的受控读取范围。
- `Project Context` 只传与当前 feature 相关、且已由代码或测试验证的地图子集和证据；不得包含完整 `project-map.md`。
- `Workspace Context` 必须让 worker 识别并保留用户已有改动，不得把用户修改误判为当前任务产物。
- `Runtime Context` 必须来自与当前宿主实际注册工具匹配的平台 flow；`Platform flow` 标识 Coordinator 已加载的具体平台流程文件。平台工具缺失、信号冲突或能力不足时 fail closed。
- `Authorization mode` 固定为 `atomic`：Coordinator 在派发前完成版本核对、执行环境验证和 Git runner verify（非 Git 项目为 workspace 边界验证），把绑定 `Task ID` 与三个版本的完整 `Authorization Evidence` 随 packet 一次性交付；`Environment verification` 为已完成的 verify 证据，`Write permission` 恒为 `granted`。worker 校验并返回 handshake 后直接执行，不等待第二次 Coordinator 消息或用户输入。任一字段不得让 worker 自行补全、推断或伪造。
- `Git Context` 必须来自 `git-workflow.sh` 的实际输出和批准后的准备结果；worker 只验证并使用指定 worktree，不拥有 Git 状态写权限。
- 不得包含完整 agent transcript、原始全量日志、其他 feature 的实现历史或无关代码。

依赖只能引用同一 task package 中的 Task ID。预计写入同一文件、修改同一公共接口或依赖未稳定中间契约的 nodes 必须建立依赖，不能同时派发。

审批必须明确列出 branch、worktree、commit、push 副作用。`Remote publish authorization: denied` 时只保留本地 commit；不得调用 push。

批准后不得改变 Goal、Acceptance criteria、Dependencies、Shared interfaces、Allowed write paths、重大风险、Git mode 或外部副作用。只读上下文补充可递增 `Context version`；改变范围时必须递增 Plan/Task version、使旧批准失效并重新审批。
