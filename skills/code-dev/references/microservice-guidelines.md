# Java Microservice Guidelines

Use this file together with `java-guidelines.md`. Both are mandatory. Existing repository conventions do not override them; a project governed by a company standard follows that standard instead, per the precedence rules in [`../SKILL.md`](../SKILL.md).

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

The shared module is named `common-api/`. Projects using `base-service`, `common`, `platform-core`, or `shared-kernel` are migrated to `common-api/` rather than kept under their existing name.

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

If a shared module already exists, keep its scope and migrate its name to `common-api/`. Its existing contents are preserved; only the module name and layout change.

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

An existing one of these is flattened into composition unless the user explicitly asks for it to stay.

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
