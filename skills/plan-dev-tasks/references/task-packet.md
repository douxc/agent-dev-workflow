# Execution Packet 接口

每个 packet 只描述一个可独立执行和验证的 feature：

```text
Required skill: dev-with-tdd
Approval state: pending | approved
Plan version:
Context version:
Task version:
Task ID:
中文标题:
Task workspace:
Goal:
Acceptance criteria:
In scope:
Out of scope:
Dependencies:
Shared interfaces:
Allowed write paths:
Allowed discovery paths:
Forbidden paths:
Forbidden side effects:
Stop conditions:
Project Context:
  Source fingerprint:
  Relevant map entries:
  Applicable constraints:
  Local overrides:
  Verified source paths:
  Relevant tests:
  Code evidence:
Workspace Context:
  Baseline fingerprint:
  Relevant file fingerprints:
  Existing user changes:
TDD classification: required | not required
TDD reason:
Red test plan:
Green implementation plan:
Focused verification:
Expanded verification:
Language check: passed
```

## 内容边界

- `Allowed write paths` 是硬写入边界；必须使用具体项目相对路径或不会意外扩大的窄 pattern。
- `Allowed discovery paths` 可包含目标文件、直接依赖、相关类型、测试、项目指令和局部注释的受控读取范围。
- `Project Context` 只传与当前 feature 相关、且已由代码或测试验证的地图子集和证据；不得包含完整 `project-map.md`。
- `Workspace Context` 必须让 worker 识别并保留用户已有改动，不得把用户修改误判为当前任务产物。
- 不得包含完整 agent transcript、原始全量日志、其他 feature 的实现历史或无关代码。

依赖只能引用同一 task package 中的 Task ID。预计写入同一文件、修改同一公共接口或依赖未稳定中间契约的 nodes 必须建立依赖，不能同时派发。

批准后不得改变 Goal、Acceptance criteria、Dependencies、Shared interfaces、Allowed write paths、重大风险或外部副作用。只读上下文补充可递增 `Context version`；改变范围时必须递增 Plan/Task version、使旧批准失效并重新审批。
