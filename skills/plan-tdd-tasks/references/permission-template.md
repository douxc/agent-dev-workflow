# 权限规则模板（init 复用）

`references/init.md` 步骤 1 在业务仓库写入 `.claude/settings.local.json` 时使用本模板。init 将 `<PROJECT_ROOT>` 替换为 `git rev-parse --show-toplevel` 输出的项目根绝对路径**去掉开头的 `/`** 后的形式（如 `/Users/me/repo` → `Users/me/repo`），与模板自带的 `//` 前缀拼成文件系统根锚定的规则：Claude Code 中单 `/path` 锚定在 settings 源位置，`//path` 才是绝对路径，直接整段替换会产生 `///Users/...` 三斜杠规则。文件写入放行必须用 `Edit` 规则：Claude Code 官方文档确认 `Write(path)` 规则从未被咨询，写入检查只走 `Edit(path)` 与 `Read(path)`。本模板全部规则都写入 `permissions.allow`，不设保留询问的 ask 分组。

## allow：通用基线

任何项目都适用，与语言无关，init 直接纳入：

- `Read(//<PROJECT_ROOT>/**)` —— 读整个项目
- `Edit(//<PROJECT_ROOT>/**)` —— 编辑与新建整个项目内的文件（写入以 Edit 规则为准，Write 规则无效）
- `Bash(git:*)` —— 全部 git 子命令（status/log/add/commit/checkout/merge/push 等）
- `Bash(bash:*)` —— 完整 bash 脚本执行
- `Bash(sh:*)` —— 完整 sh 脚本执行
- `Bash(zsh:*)` —— 完整 zsh 脚本执行
- `WebSearch` —— 完整网络搜索（裸工具名即全放行）
- `WebFetch` —— 完整网页抓取（裸工具名即全放行）
- `Read(~/.claude/**)` —— Claude Code 配置目录（本机）只读；`~` 受支持，`$HOME` 不展开
- `Read(~/.claudeP/**)` —— Claude Code 平台备根（本机）只读

## allow：按语言取舍

测试命令因语言而异，init 按实际检测到的项目形态选取对应项（shell 语法检查 `Bash(bash -n:*)`/`Bash(sh -n:*)` 已被通用基线的 `Bash(bash:*)`/`Bash(sh:*)` 覆盖，不再单列）：

- Python：`Bash(python3 -m unittest:*)`
- Node：`Bash(npm test:*)`
- Rust：`Bash(cargo test:*)`
- Go：`Bash(go test:*)`
