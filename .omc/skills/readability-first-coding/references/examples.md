# Examples

## Correct: Local Repeated Logic

`CreateOrderRequest` and `UpdateOrderRequest` each contain their own validation.

**Why correct:** The user did not request extraction. Each class can be understood without navigating to another file. If the two validations diverge in the future, changes are local and isolated.

```java
// CreateOrderRequest.java
public void validate() {
    if (productId == null) throw new IllegalArgumentException("productId is required");
    if (quantity == null || quantity <= 0) throw new IllegalArgumentException("quantity must be greater than 0");
}

// UpdateOrderRequest.java
public void validate() {
    if (productId == null) throw new IllegalArgumentException("productId is required");
    if (quantity == null || quantity <= 0) throw new IllegalArgumentException("quantity must be greater than 0");
}
```

## Incorrect: Unsolicited Extraction

```text
common/
└── validator/
    └── OrderRequestValidator.java
```

**Why incorrect:** The user did not ask for this. It adds a file, creates a dependency from both request classes to a shared validator, and forces readers to jump to a third file to understand validation rules that were perfectly readable inline.

## Correct: Direct Service Implementation

```java
@Service
public class OrderService {
    public void cancelOrder(Long orderId) {
        OrderEntity order = orderMapper.selectById(orderId);
        if (order == null) {
            throw new OrderNotFoundException(orderId);
        }
        if (!order.getStatus().equals("PENDING")) {
            throw new IllegalStateException("Only pending orders can be cancelled");
        }
        order.setStatus("CANCELLED");
        orderMapper.updateById(order);
    }
}
```

**Why correct:** All cancellation logic in one method, readable top-to-bottom. No jumping to other files.

## Incorrect: Unnecessary Layers

```text
OrderCancelHandler
OrderCancelProcessor
OrderCancelStrategy
OrderStateMachine
OrderDomainService
```

**Why incorrect:** A simple status update with two guard conditions does not need a state machine, strategy pattern, or domain service. These layers obscure a 10-line operation behind 4–5 files.

## Correct: Concrete Service, No Interface

```java
@Service
public class OrderService {
    // all methods here
}
```

**Why correct:** There is only one implementation. No interface means one less file to open, one less indirection.

## Incorrect: Interface + Impl by Default

```java
public interface OrderService { ... }

@Service
public class OrderServiceImpl implements OrderService { ... }
```

**Why incorrect:** Unless multiple implementations exist or the project already has this convention, the interface serves no purpose and adds a file for the reader to chase.

---

## Python Examples

### Correct: Direct Dataclass Validation

```python
# dto/request/create_order_request.py
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

**Why correct:** Each DTO owns its validation. No shared base class or mixin.

### Incorrect: Unsolicited ABC

```python
# base/request.py — DO NOT CREATE unless user explicitly requests it
from abc import ABC, abstractmethod

class BaseRequest(ABC):
    @abstractmethod
    def validate(self) -> None:
        ...
```

**Why incorrect:** An abstract base class for two dataclasses adds an import, a file to jump to, and no value the inline approach didn't already provide.

### Correct: Concrete Service, No ABC

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

**Why correct:** One class, all logic visible, no inheritance or interface indirection.
