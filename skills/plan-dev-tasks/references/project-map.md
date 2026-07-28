# Project Map 契约

地图固定为 `${PROJECT_ROOT}/project-map.md`，标题固定为 `# Project Map`，包含以下分区：

```text
## Architecture
## Routes
## Pages
## Components
## Constraints
```

前四个分区一行一个稳定唯一 key，使用项目相对路径并按 key 排序：

```text
- `router-entry` → `src/router/index.ts`
- `/settings/profile` → `src/pages/settings/ProfilePage.tsx`
- `shared/UserAvatar` → `src/components/UserAvatar/index.ts`
```

`Constraints` 只记录有可靠证据、范围明确且必须遵守的项目级硬约束或长期 exception：

```text
- `constraint-key` | scope: `明确范围` | rule: `必须遵守的规则` | permanent exceptions: `none` | evidence: `仓库指令、代码、测试或 human-approved`
```

不得记录任务历史、功能状态、测试细节、计划、完整 diff、agent 日志、建议、个人偏好、从少量样本推断的规则或临时局部覆盖。

## 使用

读取地图后返回：

```text
Project map status: usable | stale | missing
Project map fingerprint:
Map entries used:
Verified source paths:
Applicable constraints:
Local overrides:
Code evidence:
Expected map impact: none | update | initialize
Affected map keys:
```

地图只提供候选位置。必须用实际代码和测试验证相关条目，不得因地图存在而跳过验证。局部注释或 annotation 只在明确 scope 内覆盖地图约束，并记录为 `Local overrides`。

## 写入与冲突

Coordinator 是唯一写入者；planning、implementation 和其他 worker 不得读取完整地图，也不得写入。Coordinator 只把经过代码验证的相关子集写入 Execution Packet。写入前保存并校验 SHA-256 fingerprint，重新读取最新文件，只按受影响 key 进行 upsert/delete，保留所有不相关条目。

本地文件相对基线发生变化时：

- 不同 key 的变化自动保留并合并。
- 同一 key 被双方不同修改，或一方删除另一方修改时停止，返回 Base、Local、Proposed 的紧凑差异并请求 human decision。
- 代码位置与旧地图冲突时，以已验证的最终代码为候选事实，但不得静默覆盖并发的同 key 修改。

## 全局初始化或刷新

仅由 `$plan-dev-tasks` 在 human 明确要求时执行。使用 `rg --files` 或等效文件枚举建立结构候选，选择性读取入口、路由、页面、组件 export、构建清单、仓库指令和硬约束证据。排除 `.git`、`.tmp`、Git ignored、依赖目录、构建产物、coverage、缓存、生成文件和二进制文件。

全局扫描不等于把每个文件完整载入上下文。先生成候选地图和差异，human 确认后再写入。初次普通任务只允许初始化本次实际读取并验证的局部条目。
