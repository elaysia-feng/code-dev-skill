# Java Microservice Guidelines

本文与 `java-guidelines.md` 配合使用。新增代码遵循规范；既有结构按 [`../SKILL.md`](../SKILL.md) 的“既有项目迁移”规则先询问用户，同意后全量迁移，不同意则仅新增部分采用新规范。公司规范的优先级见同一入口文件。

## Service ownership

Each service must own its domain behavior and data contracts unless the system defines a shared contract module.

Example:

```text
project-parent/
├── order-service/
├── product-service/
├── user-service/
└── common-api/             # optional, only when genuinely shared
```

新建共享模块使用 `common-api/`。既有 `base-service`、`common`、`platform-core` 或 `shared-kernel` 仅在用户同意全量迁移后改名；不同意时保留并复用已有模块。

## Business module shape

First identify how the Maven project organizes business code.

### Normal service module

If each microservice is a regular Spring module, business contracts live under `service/`, with implementations under `impl/`:

```text
com.example.order/
├── controller/
├── dto/
├── service/
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

Do not add another nested `service/` package inside a dedicated `biz` domain merely to imitate a monolith. The `biz/<domain>/` package itself is the business-contract boundary.

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

已有共享模块保持原有职责范围；仅在用户同意全量迁移后调整名称为 `common-api/` 及相应布局，并同步依赖引用。不同意时沿用已有模块，不另建重复实现。

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

既有此类继承结构仅在用户同意迁移后调整为组合；不同意时保留，不因本规范自动重构。

## Service communication

Choose communication based on the requirement and existing architecture; do not introduce infrastructure just because the project is a microservice system.

Typical choices:

- synchronous request/response for immediate queries or commands that need an immediate result
- message broker/event for asynchronous workflows, decoupling, fan-out, or eventual consistency
- gateway for external traffic routing when the system already has/needs one

Do not replace an existing Feign/WebClient/MQ pattern with another style without a requirement.

## Transactions and consistency

Do not assume a local database transaction can provide atomicity across services.

When a workflow spans services, preserve the architecture already chosen by the system (event-driven consistency, outbox, saga/compensation, Seata, etc.). Introduce a distributed-transaction mechanism only when the task actually requires cross-service consistency and the trade-off is justified.

## DTO/entity boundaries

Do not expose one service's persistence entity as another service's contract. Cross-service APIs/events should use explicit contract DTOs or schemas owned by the integration boundary.

## Configuration and infrastructure

Do not create wrappers around Redis, RabbitMQ, Kafka, HTTP clients, or service discovery merely to hide one library call. Create an adapter/service when it owns meaningful configuration, retries, serialization, error translation, observability, or a stable integration boundary.
