# Agent Dev Workflow

一套面向 Codex、Claude Code 与 Hermes 的开发任务协作 skill bundle。它由两个必须成对安装的 skill 组成：

- `plan-dev-tasks`：唯一面向用户的入口，负责分析、分级、审批、调度、复核与项目地图维护。
- `dev-with-tdd`：仅由 Coordinator 调用的内部执行 worker，负责按已批准的 Execution Packet 完成单个 feature。

日常使用时只调用：

```text
$plan-dev-tasks
```

不要直接向 `$dev-with-tdd` 提交自然语言开发需求；它只接受由 Coordinator 派发、版本完整且已批准的 Execution Packet。

## Runtime Adapter 架构

workflow core 保持平台无关，只维护 Analysis、Execution Packet、TDD、Review、Git runner、Project Map、Cleanup 和统一状态机。平台识别与能力核验完成后，Coordinator 只加载一个匹配的 runtime adapter：

```text
plan-dev-tasks core
├── Analysis / Execution Packet / TDD / Review
├── Git runner / Project Map / Cleanup
└── Runtime Adapter Contract
    ├── Codex Adapter
    ├── Claude Code Adapter
    └── Hermes Adapter
```

平台信号冲突、adapter 缺失、worker transport 不可用或结果回传无法认证时一律 fail closed；共享 core 不跨平台降级，也不会在主上下文中冒充独立 worker。

每个 packet 使用同一生命周期：

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

Coordinator 收到 worker handoff 后必须立即进入 `reviewing` 并独立检查实际 diff 与验证证据，无需用户输入“继续”来唤醒审查。`dispatched`、`running`、`handoff-received` 或 `reviewing` 都不是可正常结束的状态。

### 平台差异

| 平台 | Human approval | Worker transport | 授权 | 完成回传 |
| --- | --- | --- | --- | --- |
| Codex | `request_user_input`；Default mode 使用精确文本 fallback | `spawn_agent`，同一 worker handle 续发 | `two-phase`：handshake 后由 Coordinator 授权 | `wait_agent` 与 mailbox 最终 handoff |
| Claude Code | Plan mode 使用 `ExitPlanMode`，否则 `AskUserQuestion` | `Agent(dev-with-tdd)` custom agent | `atomic`：Adapter v2 gate 后绑定完整授权，worker 不等待第二条消息 | 前台 Agent 结果；并行时使用宿主 completion notification 与结果聚合 |
| Hermes | Coordinator 使用 `clarify` | `delegate_task` child | `atomic`；child 不得调用 `clarify` | 会话 `result reinjection`，或 stateless 宿主同步返回 |

平台的可见性不强行统一：Claude Code 在 `/agents` 显示持久命名 custom agents；Codex 使用 skill metadata 和原生 runtime agent tree；Hermes 通过 `/skills` 发现共享 skills，delegate children 是临时运行实例。skill 的可见性不能代替平台原生 worker transport。

### Claude Code post-approval dispatch gate

Claude Code Adapter v2 将 `ExitPlanMode` 或 `AskUserQuestion` 的批准结果严格限制为 `approved`，不授予 Coordinator 业务写权限。任何实现工具前，Coordinator 必须运行版本绑定的 post-approval gate：核对 approval event、三个版本、Task ID、dispatch mode 与 `Agent(dev-with-tdd)` transport；Git 项目执行 runner `verify --require-clean`，非 Git 项目复核 workspace fingerprint。

批准后出现新的 Coordinator 业务 diff 时，以 `coordinator_direct_write` 阻断并保留现场，不 rollback、stash、clean、commit 或 accepted。`L1`、`L2` 和单 worker 强制 `foreground`；实际后台执行与批准不符时以 `dispatch_mode_mismatch` 阻断。只有明确批准的 `L3` `background-aggregate` 可以后台运行，并且必须依赖宿主 `host completion notification` 与 `result aggregation`；禁止 busy polling，不得通过 shell、目录列表或紧密循环探测完成状态。

## 纯 Git workflow

Git 仓库任务采用 provider-neutral 的纯 Git workflow。任务开始前，Coordinator 通过随 skill 发布并经过测试的 shell runner 检查仓库并 fetch 默认分支，再按 Git ancestry 而非提交时间选择最新安全 main：远端线性领先时只接受 fast-forward，本地线性领先时保留本地 HEAD，真正分叉时停止。runner 输出的本地默认分支 `Base SHA` 成为所有新 task branch 的共同基线。

系统与 Git 状态性操作遵循 shell-first：prompt 负责决策和结构化参数，runner 负责 branch、worktree、依赖软链接、commit、push 与清理。脚本能力缺失或校验失败时停止，不用临时拼接命令绕过。

- 串行任务共用一条 task branch 和当前主工作区，不创建 worktree。
- 只有实际同时执行、无依赖且无写入冲突的并行任务才创建项目根目录 `.tmp/<task-id>/worktrees/<packet-id>/` 下的独立 worktree。
- 并行任务可按 packet 声明创建 `node_modules` 等受控依赖软链接；共享前必须校验 Git ignore、manifest/lockfile fingerprint，构建输出、数据库和运行时状态不得共享。
- 每个验收通过的 packet 形成一个 commit。只有 human approval 明确授权远端发布时才只推送 task branch。

核心流程不自动 merge 默认分支、不 force push、不删除远端分支，也不包含 PR/MR 或其他 provider adapter。

## 一键安装

克隆仓库后运行根目录脚本：

```bash
git clone https://github.com/douxc/agent-dev-workflow.git
cd agent-dev-workflow
./install.sh
```

脚本始终将两套共享 skill 成对复制到 canonical 位置：

```text
~/.agents/skills/plan-dev-tasks
~/.agents/skills/dev-with-tdd
```

Claude Code 的两个 custom agent definitions 另行 canonical 安装到：

```text
~/.agents/platforms/claude-code/agents/
```

安装器检查 `~/.claude`、`~/.claudeD`、`~/.claudeP`、`~/.codex` 与 `~/.hermes`。仅当平台根目录已经存在时，才创建其 `skills/` 子目录，并为两套共享 skill 创建指向 canonical 位置的绝对软链接；平台根目录不存在时输出 `skip`，不会代为创建。

仅对已经存在的 `~/.claude`、`~/.claudeD` 和 `~/.claudeP`，安装器创建 `agents` 到 Claude canonical definitions 的绝对软链接。它不会创建 `.codex/agents` 或 `.hermes/agents`，也不会修改任何平台的默认 agent、权限或全局配置。Claude Code 安装新增 definitions 后，需要启动新会话或重启现有会话才能在 `/agents` 中看到它们。

脚本可以重复运行。每次运行时，安装器只处理上述计算出的精确目标：对既有 canonical 安装和平台链接目标（包括指向正确位置的软链接）执行永久删除，即先删除再全新安装或建链。此操作不可恢复；安装器不会创建新的 `.backup.*`，也不会扫描或删除邻接的历史 `.backup.*` 文件。`HOME`、源 skill、源 agent definition 与既有平台 `skills/` 容器都会在首次删除前完成校验。

## 仓库结构

```text
.
├── README.md
├── install.sh
├── project-map.md
├── adapters/
│   └── claude-code/
│       └── agents/
│           ├── plan-dev-tasks.md
│           └── dev-with-tdd.md
├── skills/
│   ├── plan-dev-tasks/
│   │   └── references/
│   │       ├── runtime-adapters.md
│   │       ├── runtime-codex.md
│   │       ├── runtime-claude-code.md
│   │       └── runtime-hermes.md
│   └── dev-with-tdd/
└── tests/
    ├── test_documentation.py
    └── test_install.py
```

Claude 的文件型定义位于 `adapters/claude-code/agents/`；Codex 与 Hermes 不需要对应的 `agents/` 目录。`skills/` 下的内容是发布副本，行为契约和测试随各 skill 一并发布。

## 验证

可在仓库根目录运行完整契约测试、Shell 语法检查和 diff 检查：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s skills/plan-dev-tasks/tests -p 'test_*.py'
python3 -m unittest discover -s skills/dev-with-tdd/tests -p 'test_*.py'
bash -n install.sh
git diff --check
```
