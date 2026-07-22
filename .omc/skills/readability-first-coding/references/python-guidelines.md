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

## DTO

Use dataclasses or Pydantic models for request/response data:

```python
# dto/request/create_order_request.py
from dataclasses import dataclass

@dataclass
class CreateOrderRequest:
    product_id: str
    quantity: int

    def validate(self) -> None:
        if not self.product_id:
            raise ValueError("product_id is required")
        if self.quantity is None or self.quantity <= 0:
            raise ValueError("quantity must be greater than 0")
```

```python
# dto/request/update_order_request.py
from dataclasses import dataclass

@dataclass
class UpdateOrderRequest:
    product_id: str
    quantity: int

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
- Introduce decorator-based validation unless the user requests it
- Apply design patterns the user did not ask for
- Split a readable single-module implementation across many files

User says "implement feature" → implement only that feature. User says "refactor" → then refactor.

## When User Requests Extraction

| Shared Content | Location |
|---|---|
| Shared Pydantic models, exceptions, enums, response models | `common/` |
| Stateless utilities (date_utils.py, string_utils.py) | `util/` |
| Explicitly requested base classes | `base/` |

Only extract what the user specified. Keep the extraction minimal.
