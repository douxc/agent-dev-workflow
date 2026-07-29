# 纯 Git Workflow 协议

本协议只定义 Git 仓库中的本地分支、worktree、commit 与可选 push 生命周期，不绑定代码托管 provider，也不创建任何 provider 的 PR/MR。Coordinator 是唯一 `Git owner`；worker 只在指定 worktree 修改允许路径并运行测试。

## 1. Shell-first 执行边界

prompt 负责决策和结构化参数；状态性 Git 或系统操作必须调用随 skill 发布、经过测试的 shell runner：

`scripts/git-workflow.sh`

runner 支持 `inspect`、`sync`、`prepare-serial`、`prepare-parallel`、`verify`、`commit`、`push`、`cleanup-parallel`。branch、worktree、依赖软链接、commit、push 与 worktree cleanup 不得由 prompt 临时拼接命令完成，即不得临时拼接等价状态操作。所需状态性子命令缺失或失败时必须 fail closed，保留现场并报告 `blocked`、`context_gap` 或重新规划。

允许直接执行单个只读发现命令，例如确认远端列表或读取 remote ref；每条命令必须目的单一，不得借此组合状态性操作。human approval 使用平台原生交互，文件内容编辑使用宿主安全编辑能力，两者都不由 shell 模拟。

runner 输出是稳定的 `key<TAB>value` 数据。Coordinator 只按字段解析和传递，不得 `eval` 或 `source` 输出，也不得把用户文本拼成可执行命令。

## 2. 任务开始前同步

Git 仓库任务必须在生成 `Analysis Brief` 前调用 runner `inspect`。先验证 canonical project root、当前 branch、HEAD、clean 状态、进行中的 Git 操作、worktree 与 remote/default branch 发现结果。

紧随 `inspect` 的 `sync` 是 feature approval 前唯一允许的状态性 Git 例外；它只允许在 clean default branch 执行 fetch + ff-only 基线同步。branch、worktree、commit、push 及其他 Git 副作用在批准前仍禁止，不得借同步阶段提前执行。

有 remote 时紧接着调用 `sync`：

- remote 优先来自当前 upstream，其次是唯一可解析 remote。
- 默认分支优先使用 remote HEAD，再按现有 ref 回退 `main`、`master`；仍不唯一时停止，不猜测。
- `sync` 执行 fetch，并只允许 fast-forward 更新本地默认分支。
- dirty、local ahead、diverged、detached、进行中的 Git 操作或同步失败均为 `blocked`；不执行 reset、rebase 或 stash。
- 成功后把 runner 输出的 `Base SHA` 作为本次所有新 task branch 的唯一基线，同时记录 remote default tip。

只有经只读发现确认仓库没有 remote 时才进入 `local-only`。`inspect` 因无法解析 remote 而失败后，Coordinator 可以用目的单一的只读命令确认 remote 列表为空，再读取本地默认分支与 HEAD，并调用 `verify --require-clean` 校验 branch、Base SHA、clean 状态和进行中的 Git 操作；其他 `inspect` 失败仍然 fail closed。local-only 记录本地默认分支 HEAD 为 `Base SHA`，禁止 push。

## 3. 模式与分支准备

所有新 task branch 都基于同步完成后的同一个 `Base SHA`，准备动作仅在审批覆盖其副作用后执行。

### serial

依赖串行 packet 共用一条 task branch 和当前主 worktree。Coordinator 对整个串行序列只调用一次 `prepare-serial`，后续 accepted packet 继续在该分支追加 commit，并把前一个 commit 更新为下一个 packet 的 `Expected HEAD`。串行模式不创建 worktree，也不调用 worktree cleanup。

### parallel

只有确实会实际同时运行、互相无依赖、Allowed write paths 无写入冲突且共享接口稳定的 packets 才使用 `prepare-parallel`。每个 packet 获得独立 task branch，全部来自同一个 `Base SHA`；worktree 固定为：

```text
${PROJECT_ROOT}/.tmp/<task-id>/worktrees/<packet-id>/
```

仅仅“理论可并行”不创建 worktree。slots 不足、实际串行调度、依赖关系、写入冲突或未稳定共享接口都必须改用 serial。

## 4. 受控依赖共享

并行 packet 只允许共享 Execution Packet 的 `Shared dependency paths` 明确列出的项目相对路径，通常如 `node_modules`。Coordinator 只有同时确认以下条件才向 `prepare-parallel` 传 `--share`：

- 源目标存在且 canonical path 位于 project root；
- 路径已被 Git ignored；
- 依赖定义、manifest 与 lockfile 相对 `Base SHA` 未改变，并记录 fingerprint；
- packet 的 Allowed write paths 和验收标准禁止修改对应 manifest、lockfile 或依赖目录。

条件不满足时不得猜测共享路径；改为串行，或使用审批中明确授权的独立安装。构建输出、数据库、运行时状态、缓存、socket、secret 和其他可变状态不得共享。

## 5. Git Context 与审批边界

每个 Git 仓库 Execution Packet 必须携带版本化 `Git Context`，以 runner 输出和已批准计划为事实来源。至少包含 mode、project root、remote/default branch、Base SHA、task branch、worktree、Expected HEAD、expected default tip、expected remote tip、Shared dependency paths/fingerprints、`Git owner: Coordinator` 与 remote publish authorization。expected default tip 是同步后的默认分支远端基线；expected remote tip 是 `push` 校验的 task branch 远端基线，两者不得混用。

human approval 必须明确覆盖将创建或改变的 branch、worktree、commit 与 push 副作用。`Remote publish authorization: denied` 时完成到本地 commit 为止，不得因 remote 存在而推送。批准失效或 Git Context 发生范围性变化时重新规划，不复用旧批准。

worker 不得执行 branch、worktree、commit、push、merge、rebase 或 cleanup，也不得切换、创建或删除 Git ref。

## 6. Dispatch、review 与 commit

`prepare-serial` 或 `prepare-parallel` 成功后，Coordinator 更新 packet 的 runner 实际输出。每次 worker 写入前都必须调用 `verify`，传入 packet 中的 exact project root、worktree、task branch 与 Base SHA，并把 runner 返回的 `head` 与 `Expected HEAD` 精确匹配；字段缺失或验证失败时不派发或不允许继续写入。

worker handoff 后，Coordinator 独立 review 实际 diff 与验证证据。结果为 accepted 才调用 runner `commit`，并把 packet 的 `Allowed write paths` 逐项作为明确 path 参数传入。一个 accepted packet 一个 commit；runner 未返回 commit SHA、出现越界 diff 或 review 未通过时不得继续。

串行序列在 commit 后更新后续 packet 的 `Expected HEAD`。并行 packet 的 commit 保留在各自 branch，不自动互相 merge 或 rebase。

Coordinator 按 project-map 契约完成地图决策后，如果地图实际变化，必须在 push 前使用 runner `commit` 只提交 exact `project-map.md`，形成独立的 Coordinator metadata commit；地图未变化时不得创建空 commit。该提交不改变“一个 accepted packet 一个 commit”，也不得混入 worker 未授权内容。

## 7. Drift 与发布

完成前再次执行 `inspect`、只读 remote drift 检查与 `verify`：

- HEAD、branch、worktree 或 clean 状态与 Git Context 不符时 blocked。
- remote 模式以任务开始时 `sync` 记录的 expected default tip 为基线，用目的单一的只读 remote-ref 查询确认是否变化；不得把 task branch 的 expected remote tip 当作默认分支基线，也不得在已检出 task branch 的 worktree 临时切换分支或拼接 fetch。
- remote default tip 发生变化时保守返回 `context_gap`，由 Coordinator 补充安全上下文；确认默认分支相关路径或共享接口变化时必须重新规划。不得自动 merge 或 rebase。
- local-only 模式重新验证本地默认分支基线；发生外部变化时同样停止。

只有 `Remote publish authorization: approved` 才调用 runner `push`。必须传 exact remote、default branch 与 `expected remote tip`；只推送 task branch。remote tip mismatch 或 non-fast-forward 时 blocked。

无论是否批准 push，都不自动 merge 默认分支，不 force push，不 rebase 已共享分支，不删除远端分支，也不创建 PR/MR。

## 8. 清理顺序

并行 worktree 仅在对应 accepted commit 已持久化、worktree clean、验证与证据提取完成后调用 `cleanup-parallel`。先由 runner 移除 exact worktree，再按 task workspace ownership 契约清理当前任务临时目录。串行模式不调用 `cleanup-parallel`。

正式 diff 不得包含任务脚本、日志、patch、缓存、诊断或 task workspace 内容。失败或 drift 必须保留现场；不得清理其他任务的 worktree、branch 或目录。
