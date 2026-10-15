# Java Microservice Guidelines

Use this file together with `java-guidelines.md`. Both apply within the authorized task scope and inherit the user/project/company precedence rules in [`../SKILL.md`](../SKILL.md). Do not expand a local change into a system-wide migration.

既有结构调整遵循 [`../SKILL.md`](../SKILL.md) 的“既有项目迁移”规则；已有会话授权或明确任务范围时直接执行，不重复询问。

## Service ownership

Each service must own its domain behavior and data contracts unless the system defines a shared contract module.

Example:

```text
project-parent/
├── order-services/
├── product-services/
├── user-services/
└── common-api/             # optional, only when genuinely shared
```

Use `common-api/` for a new genuinely shared API/event contract module unless project conventions specify otherwise. Existing shared modules are classified by their actual contents, not renamed solely to match a template; see [project structure](project-structure.md#java-microservices).

## Business module shape

First identify how the Maven project organizes business code.

### Normal service module

If each microservice is a regular Spring module, business contracts live under `services/`, with implementations under `impl/`:

```text
com.example.order/
├── controller/
├── dto/
├── services/
│   ├── OrderService.java
│   └── impl/
│       └── OrderServiceImpl.java
├── mapper/
├── entity/
├── exception/
└── config/
```

### Dedicated Maven `*.biz` module

If a larger multi-Maven project separates business logic into modules such as `community.biz`, use the `biz` domain layout instead:

```text
community.biz/
└── src/main/java/com/mware/community/biz/
    └── like/
        ├── LikeService.java
        ├── LikeRedisStore.java
        ├── LikeStreamRelay.java
        └── impl/
            ├── LikeServiceImpl.java
            ├── LikeRedisStoreImpl.java
            └── LikeStreamRelayImpl.java
```

Do not add another nested `services/` package inside a dedicated `biz` domain merely to imitate a monolith. The `biz/<domain>/` package itself is the business-contract boundary.

In both layouts, callers depend on interfaces, not implementation classes.

## Cross-service duplication

Similar code in two services is not automatically shared code.

Keep logic local when it represents separate domain rules that may evolve independently.

Extract/shared-contract code when there is a real system-wide invariant or protocol, for example:

- authentication/JWT contract used by several services
- common tracing/observability integration
- stable event/message schema
- generated API client contract
- organization-wide response/error protocol already adopted by the project

Do not move order/product/user business rules into a shared module merely to remove duplication.

## Shared modules

For an existing shared module, inspect scope and consumers before changing its structure. Keep contract ownership distinct from infrastructure implementations and domain logic. Renaming alone does not correct misplaced responsibilities; migrate only when the task requires it and update all affected dependencies.

Good shared-module contents may include stable technical contracts such as:

```text
common-api/
├── auth/
│   └── UserContext.java
├── event/
│   └── OrderCreatedEvent.java
└── response/
    └── ApiResponse.java
```

Avoid generic inheritance frameworks such as:

- `BaseController`
- `BaseService`
- `BaseMapper`
- `BaseEntity`
- `AbstractConverter`

Assess an existing base type's actual responsibility before changing it. Keep meaningful framework/domain contracts; replace boilerplate-only inheritance with composition when that refactor is within scope. A framework-provided type such as MyBatis-Plus `BaseMapper` is not a project-invented inheritance framework and is not banned merely by its name.

## Service communication

Choose communication based on the requirement and existing architecture; do not introduce infrastructure just because the project is a microservice system.

Typical choices:

- synchronous request/response for immediate queries or commands that need an immediate result
- message broker/event for asynchronous workflows, decoupling, fan-out, or eventual consistency
- gateway for external traffic routing when the system already has/needs one

Do not replace an existing Feign/WebClient/MQ pattern with another style without a requirement.

## Transactions and consistency

Also follow [runtime boundaries](runtime-boundaries.md) for transaction ownership, bounded retries, duplicate delivery and job execution.

Do not assume a local database transaction can provide atomicity across services.

When a workflow spans services, preserve the architecture already chosen by the system (event-driven consistency, outbox, saga/compensation, Seata, etc.). Introduce a distributed-transaction mechanism only when the task actually requires cross-service consistency and the trade-off is justified.

## DTO/entity boundaries

Do not expose one service's persistence entity as another service's contract. Cross-service APIs/events should use explicit contract DTOs or schemas owned by the integration boundary.

## Configuration and infrastructure

Do not create wrappers around Redis, RabbitMQ, Kafka, HTTP clients, or service discovery merely to hide one library call. Create an adapter/service when it owns meaningful configuration, retries, serialization, error translation, observability, or a stable integration boundary.
