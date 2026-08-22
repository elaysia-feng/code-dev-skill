# Java Guidelines

These are defaults for Java/Spring backend work. Existing project conventions take precedence when they are consistent.

## Mandatory `biz` package rule

If a Java module/package intentionally uses a `biz` business layer, business-behavior components under that layer must use interface + `impl/`, even when there is currently only one implementation.

Representative structure:

```text
com.mware.community.biz/
├── favorite/
│   ├── FavoriteService.java
│   ├── FavoriteRedisStore.java
│   ├── FavoriteStreamRelay.java
│   └── impl/
│       ├── FavoriteServiceImpl.java
│       ├── FavoriteRedisStoreImpl.java
│       └── FavoriteStreamRelayImpl.java
├── follow/
│   ├── FollowService.java
│   └── impl/
│       └── FollowServiceImpl.java
└── like/
    ├── LikeService.java
    ├── LikeRedisStore.java
    ├── LikeStreamRelay.java
    └── impl/
        ├── LikeServiceImpl.java
        ├── LikeRedisStoreImpl.java
        └── LikeStreamRelayImpl.java
```

Required conventions:

1. `<Name>.java` in the domain package is the interface/public business contract.
2. `impl/<Name>Impl.java` is the concrete implementation.
3. Put `@Service`, `@Component`, `@Repository`-style Spring stereotypes on the implementation, not on the interface.
4. Constructor injection and field types use the interface:

```java
@Service
public class CommunityFacade {
    private final LikeService likeService;

    public CommunityFacade(LikeService likeService) {
        this.likeService = likeService;
    }
}
```

Do not inject or expose:

```java
private final LikeServiceImpl likeService;
```

5. Apply the rule to business-behavior collaborators under `biz`, including names/roles such as `Service`, `Store`, `Relay`, `Manager`, `Handler`, `Processor`, and gateway/client adapters.
6. Do not force interface + impl onto data-only/framework-definition types: DTO/entity/value objects, enums, exceptions, annotations, configuration classes, constants, and similar non-behavior types.
7. A single implementation is **not** a reason to skip the interface inside `biz`; the `biz` layer deliberately uses contract-first design for extensibility, replacement, testing, and consistent interception/observability boundaries.

This rule overrides the greenfield concrete-service default below.

## Service shape outside `biz`

For a greenfield package **outside an interface-first `biz` layer** with one implementation, a concrete service is acceptable:

```java
@Service
public class OrderService {
    public void cancelOrder(Long orderId) {
        // business logic
    }
}
```

Do not create `OrderService` + `OrderServiceImpl` only because "Spring projects usually do this" when the package is not governed by the `biz` rule and there is no other project convention requiring it.

Use an interface outside `biz` when there is a concrete reason, for example:

- Multiple implementations exist or are expected by an actual requirement.
- The existing package consistently exposes services through interfaces.
- The interface is a real module/API boundary.
- A framework integration or test seam genuinely depends on the contract.
- The user explicitly requests it.

### Existing interface + `impl/` convention

If neighboring services of the same role consistently use:

```text
order/service/
├── OrderService.java
└── impl/
    └── OrderServiceImpl.java
```

follow that convention for a new service of the same role.

Outside `biz`, do not automatically generalize a service-only convention to every helper/validator. Inside `biz`, however, the mandatory business-component interface rule above applies to Service/Store/Relay/Manager/etc.

Callers should depend on public contracts when the project uses them. Do not add direct dependencies on `*Impl` from unrelated packages.

## DTOs

Separate request and response models when the API already uses DTOs:

```text
dto/
├── request/
│   ├── CreateOrderRequest.java
│   └── UpdateOrderRequest.java
└── response/
    └── OrderResponse.java
```

Do not return persistence entities directly from public controllers unless that is an intentional existing convention.

Use Bean Validation (`@NotNull`, `@Size`, custom validators) when the project already uses it. Do not replace framework validation with handwritten `validate()` methods without a reason.

## Domain types, constants, and enums

Domain enums are appropriate when they model real finite states or categories:

```java
public enum OrderStatus {
    PENDING,
    PAID,
    CANCELLED
}
```

What to avoid is creating generic `CommonConstants`, `CommonEnums`, `ConstantUtil`, or similar containers only to move literals out of one or two call sites.

Prefer ownership-based placement:

```text
order/
├── entity/
├── dto/
├── service/
└── enums/
    └── OrderStatus.java
```

rather than a global dumping ground.

## Repeated logic

Do not extract code merely because two blocks look similar. Extract when they represent the same stable rule/technical concern and a shared owner is clear.

Acceptable local duplication:

```java
if (quantity == null || quantity <= 0) {
    throw new IllegalArgumentException("quantity must be greater than 0");
}
```

may legitimately appear in two independent request flows.

A shared validator becomes reasonable when several callers must obey exactly the same invariant and inconsistent fixes would be risky.

## Pass-through methods

Avoid wrappers that add no useful boundary or behavior:

```java
public void cancelOrder(Long orderId) {
    orderManager.cancel(orderId);
}
```

A thin method is still legitimate when it intentionally owns a boundary such as:

- `@Transactional`
- authorization/security checks
- metrics/tracing
- retry/circuit-breaker policy
- API/application-layer contract
- adaptation between different models
- a mandatory `biz` interface contract whose implementation is the stable interception/application boundary

Judge the boundary, not the line count.

Example: this is a legitimate thin `biz` implementation because the interface/implementation pair is an intentional business boundary and the implementation owns transaction/security behavior:

```java
public interface OrderService {
    void cancelOrder(Long orderId);
}
```

```java
@Service
public class OrderServiceImpl implements OrderService {

    private final OrderManager orderManager;

    @Override
    @Transactional
    @PreAuthorize("hasAuthority('ORDER_CANCEL')")
    public void cancelOrder(Long orderId) {
        orderManager.cancel(orderId);
    }
}
```

By contrast, an extra `OrderService -> OrderServiceDelegate -> OrderManager` chain with no added contract/policy is still unnecessary.

## Inheritance

Prefer composition or concrete classes when inheritance only saves boilerplate. Deep inheritance chains are hard to follow.

Do not apply a fixed numerical rule blindly: framework classes or established domain hierarchies may legitimately be deeper. Flag a hierarchy when understanding a concrete class requires chasing behavior through several project-owned parents with little semantic value.

## New layers and patterns

Do not introduce these solely for architectural symmetry:

- repository layer when the project currently accesses persistence directly from services
- factory/strategy/template-method classes for a single behavior
- converter layer for trivial field copies
- base controller/service/entity hierarchy
- generic manager/handler/processor wrappers around an already clear service

The Java `biz` interface + `impl/` rule is not considered speculative layering; it is an explicit project contract. Do not use this section to bypass it.

If the project already has one of these layers, preserve and use it instead of bypassing it.

## When extraction is requested

Place extracted code according to the existing repository structure first. If the project has no convention, prefer domain ownership over generic package names.

Examples:

```text
order/validation/OrderValidator.java
order/enums/OrderStatus.java
security/JwtTokenService.java
```

Use global `common/`, `util/`, or `base/` only when the extracted concern is genuinely cross-domain and that module/package has a clear purpose.
