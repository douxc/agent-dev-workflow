# 自解释代码标准

代码应让第一次接触它的人或 AI 直接理解领域含义、行为边界与控制流。代码负责表达“是什么”和“怎么做”；注释只解释代码无法表达的“为什么”。不要用删除注释代替重构。

## 规范

- 标识符必须表达领域含义，避免需要上下文猜测的缩写或泛化名称。
- 函数的输入、输出、副作用与失败方式必须能从名称、类型和结构直接识别。
- 让代码表达“是什么”和“怎么做”；若注释在说明这两点，先重命名、提取领域常量或函数并简化控制流。
- 注释只解释代码无法表达的“为什么”，例如外部约束、反直觉业务规则及安全或兼容性取舍。

## 示例 1：含义不明的命名

### Bad

```python
# Retry when the request failed fewer than three times.
if s == 2 and c < 3:
    retry()
```

`s`、`c`、`2` 和 `3` 都要求读者猜测，注释只是在翻译代码。

### Good

```python
if request_failed and retry_count < MAX_RETRY_ATTEMPTS:
    retry_request()
```

布尔条件、计数和动作直接表达业务语义，不依赖注释。

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

## 审查结论

以下任一情况说明代码尚不能自解释：

- 业务标识符依赖缩写、单字母或 `data`、`info`、`temp`、`handle`、`process` 等泛化名称；
- 布尔名称不能直接判断真假语义；
- 数字、字符串或单位缺少领域名称；
- 多个业务条件堆叠在未命名表达式或深层嵌套中；
- 注释在翻译代码，或代码语义必须依赖注释才能成立；
- 名称、类型和结构没有暴露输入、输出、副作用或失败方式。
