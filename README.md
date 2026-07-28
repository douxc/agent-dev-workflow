# Agent Dev Workflow

一套面向 Codex 与 Claude 的开发任务协作 skill bundle。它由两个必须成对安装的 skill 组成：

- `plan-dev-tasks`：唯一面向用户的入口，负责分析、分级、审批、调度、复核与项目地图维护。
- `dev-with-tdd`：仅由 Coordinator 调用的内部执行 worker，负责按已批准的 Execution Packet 完成单个 feature。

日常使用时只调用：

```text
$plan-dev-tasks
```

不要直接向 `$dev-with-tdd` 提交自然语言开发需求；它只接受由 Coordinator 派发、版本完整且已批准的 Execution Packet。

## 一键安装

克隆仓库后运行根目录脚本。请将 `<owner>` 替换为实际仓库所有者：

```bash
git clone https://github.com/<owner>/agent-dev-workflow.git
cd agent-dev-workflow
./install.sh
```

脚本始终将两套 skill 成对复制到 canonical 位置：

```text
~/.agents/skills/plan-dev-tasks
~/.agents/skills/dev-with-tdd
```

随后脚本检查 `~/.claude`、`~/.claudeD`、`~/.claudeP`、`~/.codex` 与 `~/.hermes`。仅当平台根目录已经存在时，才创建其 `skills/` 子目录，并为两套 skill 创建指向 canonical 位置的绝对软链接；平台根目录不存在时输出 `skip`，不会代为创建。

脚本可以重复运行。正确的现有软链接保持不变；既有 canonical 安装或冲突的链接目标会先移动到同级的唯一 `.backup.<时间戳>.<进程号>` 路径，再安装或建链，不会静默删除用户文件。空 `HOME`、`HOME=/`、不存在的 `HOME` 或缺少任一源 skill 时，脚本会在安装前失败。

## 仓库结构

```text
.
├── .gitignore
├── README.md
├── install.sh
├── project-map.md
├── skills/
│   ├── plan-dev-tasks/
│   └── dev-with-tdd/
└── tests/
    └── test_install.py
```

`skills/` 下的内容是发布副本，不应在打包过程中单独改写。行为契约和测试随各 skill 一并发布。

## 验证

可在仓库根目录运行：

```bash
python3 -m unittest tests.test_install -v
python3 -m unittest discover -s skills/plan-dev-tasks/tests -v
python3 -m unittest discover -s skills/dev-with-tdd/tests -v
bash -n install.sh
```
