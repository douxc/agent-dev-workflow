# Project Map

## Architecture

| key | path | role |
| --- | --- | --- |
| `workflow.planner` | `skills/plan-dev-tasks/SKILL.md` | 面向用户的规划与协调入口 |
| `workflow.worker` | `skills/dev-with-tdd/SKILL.md` | 由 planner 调度的内部单任务执行 worker |

## Routes

## Pages

## Components

## Constraints

| key | scope | rule | permanent exceptions | evidence |
| --- | --- | --- | --- | --- |
| `invocation.user-entry` | 用户开发请求 | 用户只调用 `$plan-dev-tasks`；`dev-with-tdd` 仅作为内部 worker。 | none | `skills/plan-dev-tasks/agents/openai.yaml`; `skills/dev-with-tdd/agents/openai.yaml` |
| `release.paired-skills` | `skills/plan-dev-tasks/`, `skills/dev-with-tdd/` | 两套 skill 必须原样、成对、同版本发布和安装。 | none | `README.md`; 两套 `SKILL.md` 的协作契约 |
| `workspace.temporary-root` | 仓库内任务临时资料 | 临时任务资料只进入根目录 `.tmp/`，并由根 `.gitignore` 排除。 | none | `.gitignore`; `skills/plan-dev-tasks/references/task-workspace.md` |
