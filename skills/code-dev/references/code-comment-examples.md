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

## Never invent guarantees

- Calling a method whose name contains `Async` is not proof that it never blocks.
- A class having no mutable fields is not proof that the objects it depends on are thread-safe either.
- Document only the exceptions the caller must handle and the implementation can actually throw.
- A TODO owner comes from the user or the project convention; when it is unknown, report it as to-be-confirmed instead of filling in an arbitrary name.