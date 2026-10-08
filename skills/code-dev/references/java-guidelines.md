# Java Guidelines

These are **mandatory** rules for Java/Spring backend work. They apply regardless of what the target project currently looks like — a project that does not follow them gets changed to follow them, not exempted from this file. A project covered by a company standard is governed by that standard instead; see the precedence rules in [`../SKILL.md`](../SKILL.md).

## Conditional branch braces

Every `if`, `else if` and `else` branch body **must** use braces `{}`, regardless of statement count or line breaks. Guard clauses and early returns are not exempt. A normal `else if (...) { ... }` chain is allowed; each conditional body still requires braces.

Both of these forms are prohibited:

```java
if (!authorized(authorization)) return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();

if (!authorized(authorization))
    return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
```

Required form:

```java
if (!authorized(authorization)) {
    return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
}
```

During implementation and refactoring, enforce this rule in the code being changed. During review, report unbraced branch bodies as mandatory violations. The existing checkers do not check this rule, so inspect branch bodies explicitly.

## Business interface rule

Before creating business code, identify the project shape.

### Multi-Maven / multi-module project with `*.biz`

When the project has a dedicated Maven business module such as `community.biz`, business-behavior components under that module use interface + `impl/`:

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
└── like/
    ├── LikeService.java
    ├── LikeRedisStore.java
    ├── LikeStreamRelay.java
    └── impl/
        ├── LikeServiceImpl.java
        ├── LikeRedisStoreImpl.java
        └── LikeStreamRelayImpl.java
```

Inside a dedicated `biz` module, apply interface-first design to business-behavior collaborators such as Service, Store, Relay, Manager, Handler, Processor, gateway/client adapters, and similar collaborators.

### Ordinary monolithic Spring project

When there is no dedicated Maven `*.biz` module, keep business logic under the project's `service/` package and also use interface + `impl/`:

```text
com.example.order/
├── controller/
├── service/
│   ├── OrderService.java
│   ├── PaymentService.java
│   └── impl/
│       ├── OrderServiceImpl.java
│       └── PaymentServiceImpl.java
├── mapper/
└── entity/
```

Use the singular package name (`service/`, `mapper/`, `entity/`) as shown above. A project currently using `services/` gets migrated to `service/`; both are not left in place.

### Required conventions

1. `<Name>.java` is the public business interface.
2. `impl/<Name>Impl.java` is the implementation.
3. Put Spring stereotypes such as `@Service` / `@Component` on the implementation.
4. Inject and depend on the interface type:

```java
@Service
public class CommunityFacade {
    private final LikeService likeService;

    public CommunityFacade(LikeService likeService) {
        this.likeService = likeService;
    }
}
```

Do not inject:

```java
private final LikeServiceImpl likeService;
```

5. A single implementation is not a reason to skip the interface for Java business services/components governed by this rule.
6. Do not force interfaces onto DTO/entity/value objects, enums, exceptions, annotations, configuration classes, constants, or other data/framework-definition types.

The goal is a stable contract boundary for extension/replacement, testing, AOP/interception, and observability integration.

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

Do not return persistence entities directly from public controllers. Public controllers return `dto/response/` types.

Use Bean Validation (`@NotNull`, `@Size`, custom validators) for request constraints. Do not hand-roll `validate()` methods in service code to re-check what the model layer already enforces.

## Domain types, constants, and enums

Domain enums are appropriate when they model real finite states or categories:

```java
public enum OrderStatus {
    PENDING,
    PAID,
    CANCELLED
}
```

Avoid generic `CommonConstants`, `CommonEnums`, `ConstantUtil`, or similar dumping-ground containers.

Prefer domain ownership:

```text
order/
└── enums/
    └── OrderStatus.java
```

## Repeated logic

Do not extract code merely because two blocks look similar. Extract when they represent the same stable rule/technical concern and a shared owner is clear.

A shared validator is reasonable when several callers must obey exactly the same invariant and inconsistent fixes would be risky.

## Pass-through methods

Do not judge a Service/Impl by line count alone.

A thin implementation is legitimate when it owns a real boundary such as:

- `@Transactional`
- authorization/security checks
- metrics/tracing
- retry/circuit-breaker policy
- API/application contract
- adaptation between models
- the project-required business interface boundary

Example:

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

This is not a meaningless pass-through: it owns the business contract plus transaction/security policy.

What remains suspicious is an additional chain with no new responsibility, for example:

```text
OrderService -> OrderServiceImpl -> OrderServiceDelegate -> OrderManager
```

when `OrderServiceDelegate` only forwards the call.

## Inheritance

Prefer composition or concrete implementation classes when inheritance only saves boilerplate. Flatten project-owned hierarchies deeper than two levels: replace them with composition unless the hierarchy itself is the domain contract the code is expressing.

## New layers and patterns

Do not introduce these solely for architectural symmetry:

- an extra repository layer when the project currently uses mapper access directly
- factory/strategy/template-method classes for a single behavior
- converter layer for trivial field copies
- base controller/service/entity hierarchy
- generic manager/handler/processor wrappers around an already clear flow

The required Java business `interface + impl/` pair is not considered speculative layering.

If the project already has another meaningful layer, preserve and use it instead of bypassing it.

## When extraction is requested

Place extracted code according to [`project-structure.md`](project-structure.md): domain ownership first, generic package names only for genuinely cross-domain concerns. The user's request decides *whether* to extract; it does not decide *where* the result goes.

Examples:

```text
order/validation/OrderValidator.java
order/enums/OrderStatus.java
security/JwtTokenService.java
```

Use global `common/`, `util/`, or `base/` only when the concern is genuinely cross-domain and the module/package has a clear purpose.
