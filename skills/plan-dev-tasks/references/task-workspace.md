# Task Workspace 契约

所有临时计划、测试脚本、诊断代码、日志、patch、缓存和测试输出放入：

```text
${PROJECT_ROOT}/.tmp/<task-id>/
```

首次需要临时目录时：

1. 解析并规范化 `PROJECT_ROOT`。
2. 检查根目录 `.gitignore`；不存在则创建。
3. 没有等效 root 规则时只追加 `/.tmp/`，保留原内容并保证换行正确。
4. 创建唯一任务目录和 `task-owner.json`，至少记录 `task_id`、canonical `project_root`、canonical `task_directory` 和创建者 skill。

`.gitignore` 的 `/.tmp/` 是永久的一次性基础设施变更，任务清理时不得移除。不得使用宽泛 `.tmp` 规则忽略嵌套业务目录。

清理前必须确认：

- canonical task directory 严格位于 canonical `${PROJECT_ROOT}/.tmp/` 之下；
- marker 的 task ID、project root 和 task directory 完全匹配；
- 目标不是 `.tmp` 根目录、项目根目录、软链接逃逸路径或其他任务目录。

成功时仅在代码及 `project-map.md` 均持久化、Coordinator 独立 review 和证据提取完成后清理当前任务目录；`.tmp` 为空时可以删除空目录。失败、`context_gap`、blocked 或地图冲突时保留。用户明确取消或放弃时清理当前任务目录。

禁止通配符清理、后台扫描、删除其他任务或用户文件。最终回复不得引用已经删除的日志路径。
