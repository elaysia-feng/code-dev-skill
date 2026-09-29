# 注释取舍示例

仅在需要判断注释内容时对照，不要求复制完整模板。

## 记录调用契约

下面的文档补充单位和特殊值，而不重复参数类型：

```java
/**
 * 读取租户的缓存有效期。
 *
 * @param tenantId 租户标识，不能为 null
 * @return 有效期秒数；0 表示不缓存
 */
public int cacheTtl(String tenantId) { ... }
```

Python 同样只描述调用者需要知道的语义：

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

这些是契约示例，只有实际实现满足约定时才能采用。

## 解释容易误改的约束

比起“更新状态”，下面的注释说明为什么必须带原状态条件：

```java
// 仅允许从待支付状态取消，避免覆盖并发支付成功的结果。
int updated = orderMapper.cancelIfPending(orderId);
```

多阶段业务流程按真实层级编号：例如 1.、2.、3. 表示同级阶段；1.1、1.2 表示第一阶段的子步骤；需要更深展开时可用 1.2.1。下一同级阶段继续编号为 2.，不重复使用 1.。只标记有意义的阶段，不给每条查询或赋值编号。

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

简单属性可以不写 docstring：

```python
@property
def is_active(self) -> bool:
    return self._status == Status.ACTIVE
```

## TypeScript：说明公开 API 契约

类型签名表达静态类型，TSDoc 补充单位与特殊值：

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

行注释解释容易误改的业务约束，而不是复述赋值：

```ts
// 仅当状态版本未变化时更新，避免覆盖并发写入的结果。
await repository.updateIfVersionMatches(id, expectedVersion, nextState);
```

## 不要编造保证

- 调用了名字含 Async 的方法，不足以证明它一定不阻塞。
- 类没有可变字段，不足以证明依赖对象也是线程安全的。
- 只描述调用方需要处理且实现确实可能抛出的异常。
- TODO 的负责人从用户或项目约定获取；未知时报告待确认，不能随便填一个人名。
