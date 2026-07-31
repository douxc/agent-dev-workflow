# Project Map

## Architecture

- `installer.local` → `install.sh`
- `runtime.adapter-contract` → `skills/plan-dev-tasks/references/runtime-adapters.md`
- `runtime.adapter.codex` → `skills/plan-dev-tasks/references/runtime-codex.md`
- `runtime.adapter.claude-code` → `skills/plan-dev-tasks/references/runtime-claude-code.md`
- `runtime.adapter.hermes` → `skills/plan-dev-tasks/references/runtime-hermes.md`
- `runtime.claude-code-agents` → `adapters/claude-code/agents/`
- `workflow.git-runner` → `skills/plan-dev-tasks/scripts/git-workflow.sh`
- `workflow.planner` → `skills/plan-dev-tasks/SKILL.md`
- `workflow.worker` → `skills/dev-with-tdd/SKILL.md`

## Routes

## Pages

## Components

## Constraints

- `approval.platform-native` | scope: `plan-dev-tasks human approval` | rule: `Codex 使用 request_user_input（Default mode 仅允许三项精确文本）；Claude Code 在 Plan mode 使用 ExitPlanMode 且审批计划正文必须携带三个版本与 post-approval gate continuation，非 Plan 场景使用 AskUserQuestion；Hermes 使用 clarify。未知或冲突平台 fail closed，只有绑定当前 Plan、Context、Task 版本的 approved 可进入调度，批准不授予 Coordinator 业务写权限。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/SKILL.md; skills/plan-dev-tasks/references/human-approval.md; skills/plan-dev-tasks/references/runtime-claude-code.md; skills/plan-dev-tasks/tests/test_skill_contract.py`
- `collaboration.git-shell-workflow` | scope: `Git 仓库开发任务` | rule: `runner 是 plan-dev-tasks skill 自有资源，必须从已加载 SKILL.md 所在目录解析，业务项目不得提供、复制或创建 runner。任务开始前仅允许 runner 在 clean 默认分支 fetch，并按 Git ancestry 选择最新安全 main：远端线性领先时 fast-forward，本地线性领先时保留本地 HEAD，真正分叉时停止；runner 输出的 Base SHA 是新 task branch 的基线。其余状态性 Git 操作在批准后由 Coordinator 通过 git-workflow.sh 执行。串行 packet 共用当前 worktree 与 task branch，只有实际并行 packet 使用项目 .tmp/ worktree 和受控依赖软链接；worker 保持 Git 只读，核心协议不绑定 PR/MR provider。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/SKILL.md; skills/plan-dev-tasks/scripts/git-workflow.sh; skills/plan-dev-tasks/references/git-workflow.md; skills/plan-dev-tasks/references/task-packet.md; skills/plan-dev-tasks/tests/test_git_workflow.py; skills/plan-dev-tasks/tests/test_skill_contract.py; skills/dev-with-tdd/SKILL.md`
- `installation.canonical-links` | scope: `本地 skill 与平台 agent definition 安装` | rule: `两套共享 skill 成对安装到 ~/.agents/skills，并仅为已存在的平台根创建 skills 绝对软链接；Claude 命名 agent definitions 安装到 ~/.agents/platforms/claude-code/agents，且仅为已存在的 .claude、.claudeD、.claudeP 创建 agents 绝对软链接；.codex 与 .hermes 不创建 agents；每次安装先永久删除安装器计算出的既有 canonical 与平台链接精确目标（包括正确软链接），再全新安装或建链；不创建新的 .backup.*，也不扫描或删除邻接的历史 .backup.* 文件。` | permanent exceptions: `none` | evidence: `install.sh; tests/test_install.py; README.md; skills/plan-dev-tasks/SKILL.md; skills/dev-with-tdd/SKILL.md`
- `invocation.user-entry` | scope: `用户开发请求` | rule: `用户只调用 plan-dev-tasks 入口；dev-with-tdd 仅作为内部 worker。Claude Code 可通过同名 custom agents 发现这两个角色，但不得改变入口与 worker 的职责边界。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/agents/openai.yaml; skills/dev-with-tdd/agents/openai.yaml; adapters/claude-code/agents/plan-dev-tasks.md; adapters/claude-code/agents/dev-with-tdd.md`
- `release.paired-skills` | scope: `skills/plan-dev-tasks/, skills/dev-with-tdd/` | rule: `两套 skill 必须原样、成对、同版本发布和安装。` | permanent exceptions: `none` | evidence: `README.md; skills/plan-dev-tasks/SKILL.md; skills/dev-with-tdd/SKILL.md`
- `runtime.adapter-selection` | scope: `开发 packet 的宿主运行时` | rule: `共享 core 只维护平台无关状态机，并根据认证能力证据精确加载一个 Codex、Claude Code 或 Hermes adapter；平台冲突、transport 缺失或结果来源不确定时 fail closed，不得跨平台 fallback 或在主上下文冒充 worker。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/SKILL.md; skills/plan-dev-tasks/references/runtime-adapters.md; skills/plan-dev-tasks/tests/test_skill_contract.py`
- `runtime.automatic-review` | scope: `worker 完成回传` | rule: `所有平台的可认证 handoff 都必须立即从 handoff-received 进入 reviewing；Coordinator 在 dispatched、running、handoff-received 或 reviewing 状态不得正常结束或等待普通用户消息唤醒。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/references/runtime-adapters.md; skills/plan-dev-tasks/references/runtime-codex.md; skills/plan-dev-tasks/references/runtime-claude-code.md; skills/plan-dev-tasks/references/runtime-hermes.md`
- `runtime.claude-post-approval-gate` | scope: `Claude Code 批准后至 worker running` | rule: `Claude Adapter v2 必须在任何实现工具和 prepared 前执行版本绑定 gate 与 verify --require-clean（非 Git 核对 workspace fingerprint）；Coordinator 业务写入以 coordinator_direct_write blocked，实际派发模式不符以 dispatch_mode_mismatch blocked。L1、L2 或单 worker 强制 foreground；仅已批准的 L3 background-aggregate 可依赖宿主 completion notification 与 result aggregation，禁止 shell、目录列表或紧密循环 busy polling。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/SKILL.md; skills/plan-dev-tasks/references/human-approval.md; skills/plan-dev-tasks/references/runtime-claude-code.md; adapters/claude-code/agents/plan-dev-tasks.md; skills/plan-dev-tasks/tests/test_skill_contract.py`
- `workspace.temporary-root` | scope: `仓库内任务临时资料` | rule: `临时任务资料只进入根目录 .tmp/，并由根 .gitignore 排除。` | permanent exceptions: `none` | evidence: `.gitignore; skills/plan-dev-tasks/references/task-workspace.md`
