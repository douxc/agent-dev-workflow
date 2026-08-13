# 权限规则模板（init 复用）

`references/init.md` 步骤 2 在业务仓库写入 `.claude/settings.local.json` 时使用本模板。init 将 `<PROJECT_ROOT>` 替换为实际项目根后展示规则文本，经用户同意后经 `update-config` skill 写入 `permissions`。模板只含减少权限弹窗的常用只读规则；判断性的变更操作不预放行。

## allow：通用基线

任何项目都适用，与语言无关，init 直接纳入：

- `Read(<PROJECT_ROOT>/**)` —— 读整个项目
- `Bash(git status:*)`
- `Bash(git diff:*)`
- `Bash(git log:*)`
- `Bash(git show:*)`
- `Bash(git branch:*)`
- `Bash(git rev-parse:*)`
- `Bash(git ls-files:*)`
- `Bash(git check-ignore:*)`
- `Bash(git blame:*)`
- `WebSearch`
- `WebFetch(domain:docs.claude.com)`

## allow：按语言取舍

测试与语法检查命令因语言而异，init 按实际检测到的项目形态选取对应项：

- Python：`Bash(python3 -m unittest:*)`
- bash/sh 脚本：`Bash(bash -n:*)`、`Bash(sh -n:*)`
- Node：`Bash(npm test:*)`
- Rust：`Bash(cargo test:*)`
- Go：`Bash(go test:*)`

## ask：变更类

这些是任务收尾的「人类检查点」，默认保留询问、不写入 `permissions.allow`；观察实际使用中的打扰情况后再决定是否迁移到 allow：

- `Bash(git add:*)`
- `Bash(git commit:*)`
- `Bash(git checkout:*)`
- `Bash(git merge:*)`
- `Bash(git push:*)`
