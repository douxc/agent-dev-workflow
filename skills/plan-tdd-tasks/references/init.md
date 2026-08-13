# init 模式

仅由 `SKILL.md` §12 的字面 `/plan-tdd-tasks init` 触发。init 负责权限写入、地图创建与全局漂移判定；普通 feature 不承担这些职责。

## 前置

- `git rev-parse --show-toplevel` 必须成功。
- 规划不落盘，不使用 `.tmp/`。

## 步骤

1. **权限**：读取 `${SKILL_ROOT}/references/permission-template.md`，将模板中的 `<PROJECT_ROOT>` 替换为 `git rev-parse --show-toplevel` 输出的项目根绝对路径**去掉开头的 `/`** 后的形式（如 `/Users/me/repo` → `Users/me/repo`；模板自带 `//` 前缀是文件系统根锚点，单 `/` 会锚定到 settings 源位置）。替换后展示完整规则文本（通用基线含 `Read(//<PROJECT_ROOT>/**)`、`Edit(//<PROJECT_ROOT>/**)`、`Bash(git:*)`、完整 bash/sh/zsh 放行、裸 `WebSearch`/`WebFetch`、`Read(~/.claude/**)`、`Read(~/.claudeP/**)`；按语言取舍按检测到的项目形态选取测试命令），全部规则均写入 allow，无保留询问分组。经用户同意后调用 `update-config` skill，把规则写入 `.claude/settings.local.json` 的 `permissions.allow`。拒绝则跳过。若 skill 不可用，精确报告 `update-config unavailable; permission step skipped`，跳过权限写入并继续其余步骤。
2. **生成或更新项目地图**：
   - `project-map.md` 不存在：按 SKILL.md §11.3 判定项目形态并创建。这是地图的创建时机。
   - 文件存在：执行**漂移判定**，只核对路径、命令、结构、选型、存在性等**机械可验证**事实，不做**风格性改写**。无漂移时报告“地图最新，**无需更新**”；有漂移时展示小节与理由，**经用户同意后更新**，拒绝则跳过并报告。
   - 总结高层一跳领域导航：用 LLM 可识别的**领域对象**作节点，为每个节点列出带可定位路径的**直接生产者**与**直接消费者**；不递归展开消费者或依赖。数据库结构可用于发现领域对象和关联，但**数据库结构不能单独证明生产者**，生产者必须有直接写入或生成代码证据；不确定的关系直接省略。
   - 地图允许粗粒度和缺失，但不得记录与代码证据冲突的关系；它只缩小普通任务的搜索空间，不证明影响面完整，也不直接授权 scope。
   - 这是地图的**更新时机（init）**；普通任务不执行全局漂移判定。
3. **gitignore 校验**：仅当 `.claude/settings.local.json` 已存在或本次权限步骤写入该文件时运行 `git check-ignore .claude/settings.local.json`；未忽略时向 `.gitignore` 追加该路径。
4. **收尾**：展示待提交的 `project-map.md` 与可能的 `.gitignore` 变更，只执行一次 commit。地图新建使用 `chore: init project-map`；地图更新使用 `chore: update project-map`。汇报地图生成、更新或跳过状态、权限结果和 commit sha；settings.local.json 不进入提交。收尾提交同样必须落在非 main 分支（SKILL.md §2 分支策略）；当前在 main 时停止并转人工。
