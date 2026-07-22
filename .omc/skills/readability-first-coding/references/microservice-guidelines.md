# Java Microservice Guidelines

## Service Organization

```
project-parent
├── base-service          (only if already present or user requests it)
├── order-service
├── product-service
└── user-service
```

Each service uses its own business package:

```
com.example.order.controller
com.example.order.dto.request
com.example.order.dto.response
com.example.order.service
com.example.order.mapper
com.example.order.entity
```

```
com.example.product.controller
com.example.product.dto.request
com.example.product.dto.response
com.example.product.service
```

Internal structure per service:

```
com.example.{service-name}
├── controller
├── dto
│   ├── request
│   └── response
├── service
├── mapper
├── entity
├── exception
└── config
```

## Cross-Service Duplication

Do **not** move repeated business logic from individual services into `base-service` on your own.

Even if `order-service` and `product-service` both have similar validation or similar exception types, keep each service's copy independent — unless the user explicitly requests consolidation.

## base-service Rules

If the project structure requires `base-service` to exist, keep it minimal.

When the user asks for a unified response wrapper, create only:

```
base-service
└── response
    └── Result.java
```

Do **not** add any of these without explicit user request:

- `BaseController`
- `BaseService`
- `BaseMapper`
- `BaseEntity`
- `BaseRequest`
- `BaseResponse`
- `CommonException`
- `AbstractConverter`
- Any business logic belonging to order, product, or user domains

Every addition to `base-service` must be backed by a direct user request.

## Service Communication

Implement cross-service calls directly where needed. Do not introduce an API gateway, service mesh abstraction, or event bus unless the user explicitly requires it for the current task.
