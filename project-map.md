# Project Map

## Architecture

- `installer.local` → `install.sh`
- `workflow.planner` → `skills/plan-dev-tasks/SKILL.md`
- `workflow.worker` → `skills/dev-with-tdd/SKILL.md`

## Routes

## Pages

## Components

## Constraints

- `installation.canonical-links` | scope: `本地 skill 安装与同步` | rule: `两套 skill 成对安装到 ~/.agents/skills；仅为已存在的 .claude、.claudeD、.claudeP、.codex、.hermes 平台根目录创建指向 canonical 的绝对软链接；替换冲突目标前先创建同级备份。` | permanent exceptions: `none` | evidence: `install.sh; tests/test_install.py; README.md; skills/plan-dev-tasks/SKILL.md; skills/dev-with-tdd/SKILL.md`
- `invocation.user-entry` | scope: `用户开发请求` | rule: `用户只调用 $plan-dev-tasks；dev-with-tdd 仅作为内部 worker。` | permanent exceptions: `none` | evidence: `skills/plan-dev-tasks/agents/openai.yaml; skills/dev-with-tdd/agents/openai.yaml`
- `release.paired-skills` | scope: `skills/plan-dev-tasks/, skills/dev-with-tdd/` | rule: `两套 skill 必须原样、成对、同版本发布和安装。` | permanent exceptions: `none` | evidence: `README.md; skills/plan-dev-tasks/SKILL.md; skills/dev-with-tdd/SKILL.md`
- `workspace.temporary-root` | scope: `仓库内任务临时资料` | rule: `临时任务资料只进入根目录 .tmp/，并由根 .gitignore 排除。` | permanent exceptions: `none` | evidence: `.gitignore; skills/plan-dev-tasks/references/task-workspace.md`
