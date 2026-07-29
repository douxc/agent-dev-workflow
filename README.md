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
| Claude Code | Plan mode 使用 `ExitPlanMode`，否则 `AskUserQuestion` | `Agent(dev-with-tdd)` custom agent | `atomic`：派发前绑定完整授权，worker 不等待第二条消息 | 前台 Agent 结果；并行时必须显式聚合后台结果 |
| Hermes | Coordinator 使用 `clarify` | `delegate_task` child | `atomic`；child 不得调用 `clarify` | 会话 `result reinjection`，或 stateless 宿主同步返回 |

平台的可见性不强行统一：Claude Code 在 `/agents` 显示持久命名 custom agents；Codex 使用 skill metadata 和原生 runtime agent tree；Hermes 通过 `/skills` 发现共享 skills，delegate children 是临时运行实例。skill 的可见性不能代替平台原生 worker transport。

## 纯 Git workflow

Git 仓库任务采用 provider-neutral 的纯 Git workflow。任务开始前，Coordinator 通过随 skill 发布并经过测试的 shell runner 检查仓库、同步远端默认分支，并只接受 fast-forward；同步后的默认分支 HEAD 成为所有新 task branch 的共同基线。

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

脚本可以重复运行。正确的现有软链接保持不变；既有 canonical 安装或冲突的链接目标会先移动到同级的唯一 `.backup.<时间戳>.<进程号>` 路径，再安装或建链，不会静默删除用户文件。空 `HOME`、`HOME=/`、不存在的 `HOME` 或缺少任一源 skill/agent definition 时，脚本会在安装前失败。

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
