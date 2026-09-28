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

多阶段流程可以编号，但不要给每条查询或赋值加一个步骤。简单属性可以不写 docstring：

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
