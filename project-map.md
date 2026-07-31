# Project Map

## Architecture

- `installer.local` -> `install.sh`
- `runtime.flow-claude-code` -> `skills/plan-dev-tasks/references/claude-code-flow.md`
- `runtime.flow-hermes` -> `skills/plan-dev-tasks/references/hermes-flow.md`
- `runtime.claude-code-agents` -> `adapters/claude-code/agents/`
- `workflow.git-runner` -> `skills/plan-dev-tasks/scripts/git-workflow.sh`
- `workflow.planner` -> `skills/plan-dev-tasks/SKILL.md`
- `workflow.worker` -> `skills/dev-with-tdd/SKILL.md`

## Routes

## Pages

## Components

## Constraints

- `approval.platform-native` | scope: `plan-dev-tasks human approval` | rule: `Claude Code 在 Plan mode 使用 ExitPlanMode（审批计划正文必须携带三个版本与 post-approval gate continuation），非 Plan 场景使用 AskUserQuestion；Hermes 使用 clarify。未知或冲突平台 fail closed，只有绑定当前 Plan、Context、Task 版本的 approved 可进入调度，批准不授予 Coordinator 业务写权限。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/SKILL.md; skills/plan-dev-tasks/references/human-approval.md; skills/plan-dev-tasks/references/claude-code-flow.md; skills/plan-dev-tasks/references/hermes-flow.md; skills/plan-dev-tasks/tests/test_skill_contract.py`
- `collaboration.git-shell-workflow` | scope: `Git 仓库开发任务` | rule: `runner 是 plan-dev-tasks skill 自有资源，必须从已加载 SKILL.md 所在目录解析，业务项目不得提供、复制或创建 runner。任务开始前仅允许 runner 在 clean 默认分支 fetch，并按 Git ancestry 选择最新安全 main：远端线性领先时 fast-forward，本地线性领先时保留本地 HEAD，真正分叉时停止；runner 输出的 Base SHA 是新 task branch 的基线。其余状态性 Git 操作在批准后由 Coordinator 通过 git-workflow.sh 执行。串行 packet 共用当前 worktree 与 task branch，只有实际并行 packet 使用项目 .tmp/ worktree 和受控依赖软链接；worker 保持 Git 只读，核心协议不绑定 PR/MR provider。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/SKILL.md; skills/plan-dev-tasks/scripts/git-workflow.sh; skills/plan-dev-tasks/references/git-workflow.md; skills/plan-dev-tasks/references/task-packet.md; skills/plan-dev-tasks/tests/test_git_workflow.py; skills/plan-dev-tasks/tests/test_skill_contract.py; skills/dev-with-tdd/SKILL.md`
- `installation.direct-copies` | scope: `本地 skill 与平台 agent definition 安装` | rule: `两套共享 skill 成对、直接复制到每个已存在平台根的 skills/；Claude 命名 agent definitions 直接复制到每个已存在的 .claude、.claudeD、.claudeP 的 agents/；.hermes 不创建 agents；源仓库为唯一 canonical 来源，不保留单独的 canonical 副本，也不创建任何软链接；平台根不存在时 skip，不代为创建；每次安装对自身 skill 目录、agent 文件与平台容器（含旧版软链接）先永久删除再全新复制；不创建新的 .backup.*，也不扫描或删除邻接的历史 .backup.*；HOME、源 skill、源 agent 与既有 skills/、agents/ 容器须在首次删除前完成校验，容器为普通文件而非目录时 fail closed。` | permanent exceptions: `none` | evidence: `install.sh; tests/test_install.py; README.md; skills/plan-dev-tasks/SKILL.md; skills/dev-with-tdd/SKILL.md`
- `invocation.user-entry` | scope: `用户开发请求` | rule: `用户只调用 plan-dev-tasks 入口；dev-with-tdd 仅作为内部 worker。Claude Code 可通过同名 custom agents 发现这两个角色，但不得改变入口与 worker 的职责边界。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/agents/openai.yaml; skills/dev-with-tdd/agents/openai.yaml; adapters/claude-code/agents/plan-dev-tasks.md; adapters/claude-code/agents/dev-with-tdd.md`
- `release.paired-skills` | scope: `skills/plan-dev-tasks/, skills/dev-with-tdd/` | rule: `两套 skill 必须原样、成对、同版本发布和安装。` | permanent exceptions: `none` | evidence: `README.md; skills/plan-dev-tasks/SKILL.md; skills/dev-with-tdd/SKILL.md`
- `runtime.flow-selection` | scope: `开发 packet 的宿主运行时` | rule: `平台无关骨架只维护平台无关状态机，并按当前宿主实际注册的原生工具选定并只加载一个 platform flow（claude-code-flow.md 或 hermes-flow.md）：注册 ExitPlanMode/Agent 走 Claude Code，注册 clarify/delegate_task 走 Hermes；工具缺失、信号冲突、transport 缺失或结果来源不确定时 fail closed，不得跨平台 fallback 或在主上下文冒充 worker。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/SKILL.md; skills/plan-dev-tasks/references/claude-code-flow.md; skills/plan-dev-tasks/references/hermes-flow.md; skills/plan-dev-tasks/tests/test_skill_contract.py`
- `runtime.automatic-review` | scope: `worker 完成回传` | rule: `所有平台的可认证 handoff 都必须立即从 handoff-received 进入 reviewing；Coordinator 在 dispatched、running、handoff-received 或 reviewing 状态不得正常结束或等待普通用户消息唤醒。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/SKILL.md; skills/plan-dev-tasks/references/claude-code-flow.md; skills/plan-dev-tasks/references/hermes-flow.md; skills/plan-dev-tasks/references/review-checklist.md`
- `runtime.post-approval-gate` | scope: `批准后至 worker running（所有平台）` | rule: `任何实现工具和 prepared 前执行版本绑定 gate 与 verify --require-clean（非 Git 核对 workspace fingerprint）；Coordinator 业务写入以 coordinator_direct_write blocked，实际派发模式不符以 dispatch_mode_mismatch blocked。L1、L2 或单 worker 强制 foreground；仅已批准的 L3 background-aggregate 可依赖宿主 completion notification 与 result aggregation，禁止 shell、目录列表或紧密循环 busy polling。gate 不变量对所有平台相同，各 platform flow 实现平台具体步骤。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/SKILL.md; skills/plan-dev-tasks/references/human-approval.md; skills/plan-dev-tasks/references/claude-code-flow.md; skills/plan-dev-tasks/references/hermes-flow.md; adapters/claude-code/agents/plan-dev-tasks.md; skills/plan-dev-tasks/tests/test_skill_contract.py`
- `workspace.temporary-root` | scope: `仓库内任务临时资料` | rule: `临时任务资料只进入根目录 .tmp/，并由根 .gitignore 排除。` | permanent exceptions: `none` | evidence: `.gitignore; skills/plan-dev-tasks/references/task-workspace.md`
