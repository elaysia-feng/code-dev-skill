# Code Comment Examples

Consult these only when deciding what a comment should contain; copying the full template is not required.

## Document the call contract

The documentation below adds units and special values instead of repeating the parameter types:

```java
/**
 * 读取租户的缓存有效期。
 *
 * @param tenantId 租户标识，不能为 null
 * @return 有效期秒数；0 表示不缓存
 */
public int cacheTtl(String tenantId) { ... }
```

Python likewise describes only the semantics the caller needs to know:

```python
def cache_ttl(tenant_id: str) -> int:
    """读取租户的缓存有效期。

    Args:
        tenant_id: 非空租户标识。

    Returns:
        有效期秒数；0 表示不缓存。
    """
    ...
```

These are contract examples. The implementation must genuinely satisfy the contract it declares; if the code behavior does not match what the example describes, fix the comment instead of keeping a promise that does not hold.

## Explain constraints that are easy to break

Instead of "update the status", the comment below explains why the original status condition is required:

```java
// 仅允许从待支付状态取消，避免覆盖并发支付成功的结果。
int updated = orderMapper.cancelIfPending(orderId);
```

A multi-stage business flow is numbered by its real hierarchy: for example `1.`, `2.`, `3.` mark sibling stages; `1.1`, `1.2` mark sub-steps of the first stage; `1.2.1` is available when a deeper level is needed. The next sibling stage continues at `2.` and never reuses `1.`. Number only meaningful stages, never every query or assignment.

```java
public boolean cancelIfPending(long orderId) {
    // 1. 拒绝无效订单号，避免执行无意义的持久化操作。
    // 1.1 订单编号必须为正数。
    if (orderId <= 0) {
        throw new IllegalArgumentException("订单 ID 必须为正数");
    }

    // 2. 仅更新待支付订单，避免覆盖并发支付成功后的状态。
    return orderMapper.cancelIfPending(orderId) == 1;
}
```

A simple property can go without a docstring:

```python
@property
def is_active(self) -> bool:
    return self._status == Status.ACTIVE
```

Python 的私有或短函数只要包含多个业务阶段，同样需要编号；没有真实子步骤就只写同级编号：

```python
def _submit_order(order):
    # 1. 先校验订单状态，拒绝不允许提交的订单。
    validate_submittable(order)
    # 2. 保存提交结果后再通知，避免发送尚未保存的状态。
    saved = save_submission(order)
    # 3. 通知调用方，失败处理遵循当前项目的通知策略。
    notify_submission(saved)
    return saved
```

以上顺序依赖必须由实际实现支持；编号说明业务阶段，不承诺跨数据库与通知系统的原子性。

## TypeScript: document the public API contract

The type signature expresses the static type; TSDoc adds the units and special values:

```ts
/**
 * 读取租户的缓存有效期。
 *
 * @param tenantId 租户标识；不能为空。
 * @returns 有效期秒数；0 表示不缓存。
 */
export function cacheTtl(tenantId: string): number {
  // 示例实现
  return 0;
}
```

A line comment explains a business constraint that is easy to break, instead of restating the assignment:

```ts
// 仅当状态版本未变化时更新，避免覆盖并发写入的结果。
await repository.updateIfVersionMatches(id, expectedVersion, nextState);
```

前端提交流程也按业务阶段编号，不能把所有事件处理函数都当作简单函数豁免：

```ts
async function submitOrder() {
  // 1. 拒绝重复提交和不符合约束的输入。
  if (submitting.value || !validateOrder()) return;
  submitting.value = true;
  try {
    // 2. 保存订单，成功后再刷新当前页面的数据。
    await orderApi.submit(form.value);
    await refreshOrders();
  } finally {
    // 3. 成功或失败都释放提交状态，允许用户继续操作。
    submitting.value = false;
  }
}
```

异常提示由当前项目的请求/页面边界处理；示例中的状态写法按所用框架调整。

## Never invent guarantees

- Calling a method whose name contains `Async` is not proof that it never blocks.
- A class having no mutable fields is not proof that the objects it depends on are thread-safe either.
- Document only the exceptions the caller must handle and the implementation can actually throw.
- A TODO owner comes from the user or the project convention; when it is unknown, report it as to-be-confirmed instead of filling in an arbitrary name.
