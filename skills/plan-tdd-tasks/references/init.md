# init 模式

仅由 `SKILL.md` §12 的字面 `/plan-tdd-tasks init` 触发。init 负责地图创建与全局漂移判定；普通 feature 不承担这两项职责。

## 前置

- `git rev-parse --show-toplevel` 必须成功。
- 规划不落盘，不使用 `.tmp/`。

## 步骤

1. **生成或更新项目地图**：
   - `project-map.md` 不存在：按 SKILL.md §11.3 判定项目形态并创建。这是地图的创建时机。
   - 文件存在：执行**漂移判定**，只核对路径、命令、结构、选型、存在性等**机械可验证**事实，不做**风格性改写**。无漂移时报告“地图最新，**无需更新**”；有漂移时展示小节与理由，**经用户同意后更新**，拒绝则跳过并报告。
   - 这是地图的**更新时机（init）**；普通任务不执行全局漂移判定。
2. **权限**：读取 `${SKILL_ROOT}/references/permission-template.md`，将模板中的 `<PROJECT_ROOT>` 替换为实际项目根后展示规则文本（通用基线含 `Read(<PROJECT_ROOT>/**)` 等只读规则）。经用户同意后调用 `update-config` skill，把「通用基线」与「按语言取舍（按检测到的项目形态选取）」写入 `.claude/settings.local.json` 的 `permissions.allow`；「ask：变更类」默认保留询问、不写入。拒绝则跳过。若 skill 不可用，精确报告 `update-config unavailable; permission step skipped`，跳过权限写入并继续其余步骤。
3. **gitignore 校验**：仅当 `.claude/settings.local.json` 已存在或本次权限步骤写入该文件时运行 `git check-ignore .claude/settings.local.json`；未忽略时向 `.gitignore` 追加该路径。
4. **收尾**：展示待提交的 `project-map.md` 与可能的 `.gitignore` 变更，只执行一次 commit。地图新建使用 `chore: init project-map`；地图更新使用 `chore: update project-map`。汇报地图生成、更新或跳过状态、权限结果和 commit sha；settings.local.json 不进入提交。收尾提交同样必须落在 dev 分支（SKILL.md §2 分支策略）；当前不在 dev 时停止并转人工。
