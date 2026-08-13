# 自解释代码标准

代码应让第一次接触它的人或 AI 直接理解领域含义、行为边界与控制流。代码负责表达“是什么”和“怎么做”；注释只解释代码无法表达的“为什么”。不要用删除注释代替重构。

## 规范

- 标识符必须表达领域含义，避免需要上下文猜测的缩写或泛化名称。
- 存在等价的肯定谓词时，布尔变量和谓词必须使用肯定语义。`canEdit` 表示当前主体的权限或能力，`hasPermission` 表示权限持有；`isEditable` 表示对象状态。避免 `isCannotEdit` 等可直接改写的否定式名称。失败守卫可以写 `!canEdit`，因为被取反的变量本身仍是肯定语义。`isDeleted`、`isDisabled` 等真实领域状态没有自然的肯定同义词时可以保留。
- 函数的输入、输出、副作用与失败方式必须能从名称、类型和结构直接识别。
- 纯计算逻辑应提取为具名独立函数：一个函数只表达一个计算，输入、输出经由参数与返回值，与读写、持久化等副作用职责分离（高内聚、低耦合）。
- 让代码表达“是什么”和“怎么做”；若注释在说明这两点，先重命名、提取领域常量或函数并简化控制流。
- 注释只解释代码无法表达的“为什么”，例如外部约束、反直觉业务规则及安全或兼容性取舍。

## 适用边界

本标准只审查本次变更中的人工编写代码，并只否决有现实、等价改写方案的歧义：

- **生成代码与第三方代码**：由生成器、vendor 或上游依赖拥有的内容不要求重命名；若本次必须纳入变更，必须提供包内可定位的来源标记或契约证据，不能只凭目录名猜测。
- **框架、协议或公共 API**：框架生命周期名、协议字段、序列化键或兼容中的公共 API 若由外部契约固定，可以保留，但必须提供包内可定位的外部契约证据；内部新代码优先用领域包装器隔离该名称。
- **短小且作用域明显**：`i`、`x`、`y`、`e`、`err` 等约定名称只在短小、局部且领域含义从紧邻结构即可判断时允许；一旦跨越嵌套、回调或多个语义步骤就应重命名。
- `isDeleted`、`isDisabled` 等真实领域负状态不是例外漏洞：它们本来就在表达状态；只有存在自然且等价的肯定谓词时才要求改写。

## 示例 1：肯定式布尔命名

### Bad

```typescript
const isCannotEdit = user.role !== "admin";
setEditorVisibility(!isCannotEdit);
```

`isCannotEdit` 把否定编码进变量；读者必须先理解“不能”，再判断真假，后续取反时还会形成双重否定。每次使用都要先做一次心智反转，而不是按第一性直觉直接读出“可以编辑”。

### Good

```typescript
const canEdit = user.role === "admin";
setEditorVisibility(canEdit);
```

`canEdit` 直接回答“是否可以编辑”，且与 Bad 版本调用同一个动作、保持行为等价；改进只来自语义更直接的命名。若失败路径适合早退出，`if (!canEdit) return;` 仍保持单层、清晰的否定。

## 示例 2：魔法值与单位

### Bad

```python
def valid(t):
    return t < 300
```

函数用途、参数单位和 `300` 的含义都不可识别。

### Good

```python
SESSION_TIMEOUT_SECONDS = 300


def is_session_active(elapsed_seconds: int) -> bool:
    return elapsed_seconds < SESSION_TIMEOUT_SECONDS
```

名称与类型说明领域、单位、返回语义和边界常量。

## 示例 3：依赖注释的复杂控制流

### Bad

```python
def process(o):
    # Release a paid order unless it was already released.
    if o.s == "paid":
        if not o.r:
            o.r = True
```

通用函数名、缩写字段、嵌套条件和直接赋值掩盖了副作用与跳过条件。

### Good

```python
def release_order_for_fulfillment(order: Order) -> None:
    if not order.is_paid:
        raise UnpaidOrderError(order.id)
    if order.is_released_for_fulfillment:
        return

    order.mark_ready_for_fulfillment()
```

函数名、领域谓词、守卫分支和领域动作共同表达输入、失败方式、副作用与控制流。

## 示例 4：职责混杂的纯计算内联

### Bad

```python
def process_order(order: Order) -> None:
    # 满 1000 打 85 折
    if order.total >= 1000:
        order.total = round(order.total * 0.85, 2)
    order.updated_at = now()
    save(order)
```

计算规则靠注释翻译；纯计算与持久化副作用混在同一个函数里，无法独立命名、复用或测试。

### Good

```python
LARGE_ORDER_THRESHOLD = 1000
LARGE_ORDER_DISCOUNT_RATE = 0.85


def apply_large_order_discount(total: float) -> float:
    if total < LARGE_ORDER_THRESHOLD:
        return total
    return round(total * LARGE_ORDER_DISCOUNT_RATE, 2)


def process_order(order: Order) -> None:
    order.total = apply_large_order_discount(order.total)
    order.updated_at = now()
    save(order)
```

纯计算提取为具名独立函数，与读写、持久化职责分离（高内聚、低耦合）；常量携带领域含义与边界；行为与 Bad 等价（同样满 1000 打 85 折、保留两位）。

## 审查结论

对本次变更中的人工编写代码，以下任一情况说明代码尚不能自解释；命中“适用边界”的内容必须给出可定位的契约或来源证据，不因词形或文件类型自动豁免：

- 业务标识符依赖缩写、单字母或 `data`、`info`、`temp`、`handle`、`process` 等泛化名称；
- 存在自然的肯定谓词却使用 `isCannotEdit`、`isNotReady` 等否定式名称；`isDeleted`、`isDisabled` 等真实领域状态不因词形带否定含义而自动失败；
- 数字、字符串或单位缺少领域名称；
- 多个业务条件堆叠在未命名表达式或深层嵌套中；
- 纯计算逻辑内联在读写、持久化等副作用流程中，无法独立命名、复用或测试；
- 注释在翻译代码，或代码语义必须依赖注释才能成立；
- 名称、类型和结构没有暴露输入、输出、副作用或失败方式。
