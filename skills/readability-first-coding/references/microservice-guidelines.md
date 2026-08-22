# Java Microservice Guidelines

Use this file together with `java-guidelines.md`. Existing repository conventions take precedence, while Java business contracts remain interface-first.

## Service ownership

Each service should own its domain behavior and data contracts unless the system already defines a shared contract module.

Example:

```text
project-parent/
├── order-service/
├── product-service/
├── user-service/
└── common-api/              # optional, only when genuinely shared
```

Do not assume the shared module must be named `base-service`. Existing projects may use `common`, `common-api`, `platform-core`, `shared-kernel`, or no shared module at all.

## Business module shape

First identify how the Maven project organizes business code.

### Normal service module

If each microservice is a regular Spring module, business contracts live under `service/` or the project's existing `services/`, with implementations under `impl/`:

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

If a shared module already exists, preserve its scope and naming.

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

unless they are already part of the project's architecture or the user explicitly asks for them.

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
