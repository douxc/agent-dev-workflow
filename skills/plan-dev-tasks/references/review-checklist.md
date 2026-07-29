# Coordinator 独立 Review

基于用户工作区实际 diff、当前代码和可复现验证证据审查；不得只复述 worker handoff。

## 需求与范围

- 每条验收标准映射到实现和测试证据。
- 只修改批准的 `Allowed write paths`，没有越界、新增 feature 或未批准副作用。
- 保留用户已有和无关改动；没有隐藏重命名、依赖、配置、迁移或公共接口变化。
- `Context deviations` 已与真实代码核对；不能解释的偏差视为阻断问题。

## TDD 与验证

- `TDD required` 存在实现前的可信 Red，失败直接证明目标行为缺失或 bug 存在。
- Green 为最小实现；测试未被弱化；Refactor 有真实结构依据。
- `TDD not required` 确实不改变运行行为、渲染、解析、输出或公共契约。
- 聚焦测试和适度扩大验证通过，命令、退出码与结论一致。

## 结构与 UI/UX

- 遵循现有模块边界、命名、错误处理和依赖方向。
- 方案简单，没有过度设计、冗余、死代码、投机抽象或无依据 fallback。
- UI/UX 复用项目组件、token、字体、颜色、间距、图标、文案和交互模式。
- 按影响检查 loading、empty、error、disabled、hover、focus、响应式、overflow、键盘与可访问性。

## Project Map 与临时资源

- 核对 `Resource location changes`、`Constraint changes observed` 与实际 diff；handoff 只作为观察证据。
- 只按受影响 key 更新架构、路由、页面、组件位置/export 或可靠项目级硬约束。
- 同 key 并发冲突没有被静默覆盖；普通实现和临时局部 override 没有写入地图。
- 正式 diff 不含 `.tmp`、日志、诊断、patch、缓存、生成文件、secret 或无关文件。
- 代码与地图均已持久化、review 和证据提取完成后才清理当前任务目录。
- 失败、`context_gap`、blocked 或地图冲突时保留恢复现场。

## Git Workflow

- `Git Context` 的 project root、mode、Base SHA、task branch、worktree 与 runner 实际输出一致；expected default tip 和 task branch expected remote tip 未混用；worker 没有执行 Git 状态写操作。
- worker 写入前的 `verify` 通过，返回 `head` 与 `Expected HEAD` 精确匹配；worker handoff 后先完成 Coordinator 独立 review，再以 `Allowed write paths` 调用 `commit`。
- 一个 accepted packet 一个 commit；commit 后 worktree clean，正式 diff 不含任务脚本、日志或 task workspace 内容。
- `project-map.md` 发生变化时，push 前已经形成只含该文件的 Coordinator metadata commit；没有地图变化时没有空 commit。
- 完成前再次 `inspect`、检查默认分支与共享接口 drift 并运行 `verify`；drift 未被自动 merge、rebase、reset 或 stash 掩盖。
- `push` 与审批中的 remote publish authorization 一致，只推送 task branch；expected remote tip 不匹配时已经停止。
- 不自动 merge 默认分支，不 force push，不删除远端分支，不创建 PR/MR。
- 并行模式仅在 accepted commit 持久化且 clean 后先移除 worktree，再清理 task workspace；串行模式不调用 worktree cleanup。失败或 drift 保留现场。

## 语言与结论

- 用户输出、任务包、handoff 和 review 默认使用简体中文；英文只保留必要技术字面量。
- 每个 worker 结果为 `accepted`、`rework`、`context_gap`、`needs_replan` 或 `blocked`；整体结论为 `Approved`、`Changes required` 或 `Blocked`。
- 最终输出包含 `Language check: passed`。
