# Java Guidelines

## Service

When there is only one implementation, prefer a concrete class:

```java
@Service
public class OrderService {
    public void cancelOrder(Long orderId) {
        // logic here
    }
}
```

Do **not** automatically create:

```
OrderService (interface)
OrderServiceImpl
```

Create an interface only when:

- The user requests it.
- Multiple implementations actually exist.
- The existing project convention requires it.

## DTO

Separate requests and responses:

```
dto/request/CreateOrderRequest.java
dto/request/UpdateOrderRequest.java
dto/response/OrderResponse.java
```

Do not return database entities directly from controllers.

## Repeated Code

Duplicated business logic is allowed. Do not extract a shared validator unless the user explicitly asks.

**Acceptable — each class owns its validation:**

```java
public class CreateOrderRequest {
    public void validate() {
        if (productId == null) {
            throw new IllegalArgumentException("productId is required");
        }
        if (quantity == null || quantity <= 0) {
            throw new IllegalArgumentException("quantity must be greater than 0");
        }
    }
}
```

```java
public class UpdateOrderRequest {
    public void validate() {
        if (productId == null) {
            throw new IllegalArgumentException("productId is required");
        }
        if (quantity == null || quantity <= 0) {
            throw new IllegalArgumentException("quantity must be greater than 0");
        }
    }
}
```

**Unacceptable — unsolicited extraction:**

```java
// Do NOT create this unless the user asks:
OrderRequestValidator.validate(productId, quantity);
```

**Do not proactively create any of these:**

- `CommonValidator`
- `BaseOrderRequest`
- `OrderValidationUtil`
- `AbstractOrderRequest`

## Forbidden Proactive Refactorings

When implementing a feature, do **not**:

- Extract shared methods
- Extract utility classes
- Create parent classes or interfaces
- Create unified validators, converters, constant classes, or enums
- Create shared DTOs or shared Services
- Merge similar methods
- Apply Template Method, Strategy, or Factory patterns
- Split a readable single-module implementation across many files
- Modify unrelated module structure

User says "implement feature" → implement only that feature. User says "refactor" → then refactor.

## Pass-Through Methods

A method that only delegates to another method without adding logic is a pass-through wrapper. Do not create these unless explicitly requested:

```java
// DO NOT create a wrapper that only delegates
@Service
public class OrderService {
    public void cancelOrder(Long orderId) {
        return this.orderManager.cancel(orderId);
    }
}
```

**Why incorrect:** The caller could invoke `orderManager.cancel(orderId)` directly. A wrapper that only delegates obscures the real implementation location and forces readers to chase through an extra file.

## Deep Inheritance Chains

Avoid inheritance chains deeper than 2 levels (grandparent -> parent -> child). Each additional level forces readers to understand more files to know what a method actually does:

```java
// DO NOT create deep chains like:
// ExpressCancelHandler -> CancelHandler -> BaseHandler
public abstract class BaseHandler {
    public abstract void handle(Request request);
}

public class CancelHandler extends BaseHandler {
    @Override
    public void handle(Request request) { ... }
}

public class ExpressCancelHandler extends CancelHandler {
    @Override
    public void handle(Request request) { ... }
}
```

**Why incorrect:** Three levels force readers to understand all three classes. Unless the domain genuinely requires this hierarchy, flatten to one or two concrete classes.

## When User Requests Extraction

| Shared Content | Location |
|---|---|
| Shared DTOs, exceptions, enums, response wrappers | `common/` |
| Stateless utilities (DateUtil, StringUtil, JsonUtil) | `util/` |
| Explicitly requested base classes (BaseEntity, BaseController, BaseService) | `base/` |

Only extract what the user specified. If the user says "extract this validation", extract only that validation — do not also create a full base framework.
