# Agent Dev Workflow

一套面向 Codex 与 Claude 的开发任务协作 skill bundle。它由两个必须成对安装的 skill 组成：

- `plan-dev-tasks`：唯一面向用户的入口，负责分析、分级、审批、调度、复核与项目地图维护。
- `dev-with-tdd`：仅由 Coordinator 调用的内部执行 worker，负责按已批准的 Execution Packet 完成单个 feature。

日常使用时只调用：

```text
$plan-dev-tasks
```

不要直接向 `$dev-with-tdd` 提交自然语言开发需求；它只接受由 Coordinator 派发、版本完整且已批准的 Execution Packet。

## 安装到 Codex

以下示例使用 Codex 随附的官方 skill 安装脚本，从 GitHub 仓库一次安装两套 skill。请将 `<owner>` 替换为实际仓库所有者：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo <owner>/agent-dev-workflow \
  --path skills/plan-dev-tasks skills/dev-with-tdd
```

安装后可在下一个任务中使用。两套 skill 必须保持来自同一版本，不要只更新其中一套。

## 安装到 Claude

先克隆仓库：

```bash
git clone https://github.com/<owner>/agent-dev-workflow.git
cd agent-dev-workflow
```

手工复制：

```bash
mkdir -p "$HOME/.claude/skills"
cp -R skills/plan-dev-tasks "$HOME/.claude/skills/"
cp -R skills/dev-with-tdd "$HOME/.claude/skills/"
```

或者创建软链接，便于后续在仓库内统一更新：

```bash
mkdir -p "$HOME/.claude/skills"
ln -s "$(pwd)/skills/plan-dev-tasks" "$HOME/.claude/skills/plan-dev-tasks"
ln -s "$(pwd)/skills/dev-with-tdd" "$HOME/.claude/skills/dev-with-tdd"
```

如果目标位置已存在，请先确认其内容和来源，再选择覆盖、备份或改用新的克隆目录。安装或更新时始终同时处理两个 skill。

## 仓库结构

```text
.
├── .gitignore
├── README.md
├── project-map.md
└── skills/
    ├── plan-dev-tasks/
    └── dev-with-tdd/
```

`skills/` 下的内容是发布副本，不应在打包过程中单独改写。行为契约和测试随各 skill 一并发布。

## 验证

可在仓库根目录运行：

```bash
python -m unittest discover -s skills/plan-dev-tasks/tests
python -m unittest discover -s skills/dev-with-tdd/tests
```
