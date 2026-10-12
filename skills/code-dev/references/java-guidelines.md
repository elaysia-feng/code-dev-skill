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

## 配置与环境

Spring Boot 默认配置必须写入 `application.yml`，开发、测试、生产差异分别写入 `application-dev.yml`、`application-test.yml`、`application-prod.yml`，使用 Spring profiles 选择。普通 Java 或其他框架采用项目原生配置机制，不为 YAML 或 profiles 引入 Spring。遵守 [`configuration-guidelines.md`](configuration-guidelines.md) 中的加载、默认值、敏感信息和禁止硬编码要求。下面的配置绑定要求适用于 Spring 项目。

同一业务或基础设施的一组配置优先使用 `@ConfigurationProperties` 绑定到有明确归属的配置类型，并通过 `@Validated` 与校验注解检查必填值和范围；按项目机制注册配置类型。零散配置可使用 `@Value`，但禁止在注解中写入环境值或配置默认值，例如 `${client.timeout:5000}` 的默认值应移到 YAML。配置类型不需要业务接口或 `impl/`。

## 注解使用

框架已经提供适合当前职责的声明式能力时，应使用注解并确认生效，避免重复手写同等的框架逻辑。下面的框架注解规则以项目已使用相关框架为前提；普通 Java 不强行引入框架，不要求所有业务逻辑通过注解实现。

- 组件注册使用 `@Service`、`@Component`、`@Repository` 或 `@Configuration` / `@Bean` 等与职责匹配的注解；业务组件注解放在实现类上。保持构造器注入；单构造器无需添加冗余的 `@Autowired`。
- HTTP 入口使用请求映射注解；请求字段约束使用 Bean Validation 注解，并在入口使用 `@Valid` / `@Validated` 触发。跨字段、跨实体和依赖持久化状态的业务规则仍在合适的业务边界实现。
- 需要原子性的写入流程，在 public 业务入口方法使用 `@Transactional`，根据实际异常语义设置回滚规则。普通查询通常不加事务；避免慢速外部调用占用事务。
- 权限、缓存、异步和重试在确有需求、框架依赖已具备时使用相应注解；不要为了使用注解引入无关依赖或改变业务语义。
- 实现接口或重写父类方法时使用 `@Override`。采用项目已有的代码生成注解时遵循其适用范围，不为减少几行代码新增依赖。
- 必须验证注解生效所需的组件扫描、功能启用、校验依赖和代理调用链。事务、异步、缓存等代理注解不能仅靠同类自调用生效，也不能把注解放在无法被代理拦截的方法上后声称已实现功能。

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
