# Python Guidelines

## Service

When there is only one implementation, prefer a plain class or module-level functions:

```python
# order_service.py
class OrderService:
    def cancel_order(self, order_id: int) -> None:
        order = self.order_repository.find_by_id(order_id)
        if order is None:
            raise OrderNotFoundException(order_id)
        if order.status != "PENDING":
            raise ValueError("Only pending orders can be cancelled")
        order.status = "CANCELLED"
        self.order_repository.update(order)
```

Do **not** automatically create abstract base classes (ABCs) for services unless multiple implementations exist or the user explicitly requests them.

Do **not** proactively create `Protocol` classes for type hints. Use concrete types or simple type aliases instead. Protocols add indirection that obscures the real implementation without improving readability.

## DTO

Use dataclasses or Pydantic models for request/response data.

Do not return database entities directly from controllers or public API endpoints.

```python
# dto/request/create_order_request.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateOrderRequest:
    product_id: str
    quantity: Optional[int] = None

    def validate(self) -> None:
        if not self.product_id:
            raise ValueError("product_id is required")
        if self.quantity is None or self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
```

```python
# dto/request/update_order_request.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class UpdateOrderRequest:
    product_id: str
    quantity: Optional[int] = None

    def validate(self) -> None:
        if not self.product_id:
            raise ValueError("product_id is required")
        if self.quantity is None or self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
```

## Repeated Code

Duplicated validation is allowed. Each DTO owns its `validate()` method. Do not extract a shared validator unless the user asks.

**Do not proactively create:**

- `common/validators.py`
- `BaseRequest` with a generic `validate()`
- `ValidationMixin`
- `shared/exceptions.py` (unless multiple modules genuinely share the same exception types)

## Forbidden Proactive Refactorings

When implementing a feature, do **not**:

- Extract shared functions or mixins
- Create `common/` or `util/` packages
- Create abstract base classes
- Create shared DTOs or shared services
- Merge similar functions
- Introduce decorator-based validation unless the user requests it
- Create unified validators or validation utilities
- Apply design patterns the user did not ask for
- Split a readable single-module implementation across many files
- Modify unrelated module structure

User says "implement feature" → implement only that feature. User says "refactor" → then refactor.

## Pass-Through Methods

A function or method that only delegates to another callable without adding logic is a pass-through wrapper. Do not create these unless explicitly requested:

```python
# DO NOT create a wrapper that only delegates
class OrderService:
    def cancel_order(self, order_id: int) -> None:
        return self._order_manager.cancel(order_id)
```

**Why incorrect:** The caller could invoke `order_manager.cancel(order_id)` directly. A wrapper that only delegates obscures the real implementation location and forces readers to chase through an extra file.

## Deep Inheritance Chains

Avoid inheritance chains deeper than 2 levels (grandparent → parent → child). Each additional level forces readers to understand more files to know what a method actually does:

```python
# DO NOT create deep chains like:
# ExpressCancelHandler → CancelHandler → BaseHandler
class BaseHandler:
    def handle(self, request): ...

class CancelHandler(BaseHandler):
    def handle(self, request): ...

class ExpressCancelHandler(CancelHandler):
    def handle(self, request): ...
```

**Why incorrect:** Three levels force readers to understand all three classes. Unless the domain genuinely requires this hierarchy, flatten to one or two concrete classes.

## When User Requests Extraction

| Shared Content | Location |
|---|---|
| Shared Pydantic models, exceptions, enums, response models | `common/` |
| Stateless utilities (date_utils.py, string_utils.py) | `util/` |
| Explicitly requested base classes | `base/` |

Only extract what the user specified. Keep the extraction minimal.
