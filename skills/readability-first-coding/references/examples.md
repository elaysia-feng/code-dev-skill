# Examples

## Correct: Local Repeated Logic

`CreateOrderRequest` and `UpdateOrderRequest` each contain their own validation.

**Why correct:** The user did not request extraction. Each class can be understood without navigating to another file. If the two validations diverge in the future, changes are local and isolated.

```java
// CreateOrderRequest.java
public void validate() {
    if (productId == null) {
        throw new IllegalArgumentException("productId is required");
    }
    if (quantity == null || quantity <= 0) {
        throw new IllegalArgumentException("quantity must be greater than 0");
    }
}

// UpdateOrderRequest.java
public void validate() {
    if (productId == null) {
        throw new IllegalArgumentException("productId is required");
    }
    if (quantity == null || quantity <= 0) {
        throw new IllegalArgumentException("quantity must be greater than 0");
    }
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

### Correct: Pydantic Schema with Inline Validation

```python
# schemas/create_order_request.py
from pydantic import BaseModel, Field

class CreateOrderRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
```

```python
# schemas/update_order_request.py
from pydantic import BaseModel, Field

class UpdateOrderRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
```

**Why correct:** Each schema owns its validation. No shared base class or mixin. Field duplication between schemas is allowed.

### Incorrect: Unsolicited ABC

```python
# base/request.py — DO NOT CREATE unless user explicitly requests it
from abc import ABC, abstractmethod

class BaseRequest(ABC):
    @abstractmethod
    def validate(self) -> None:
        ...
```

**Why incorrect:** An abstract base class for two Pydantic models adds an import, a file to jump to, and no value the inline approach didn't already provide.

### Correct: Concrete Service, No ABC

```python
# services/order_service.py
from sqlmodel import Session
from app.models.order import Order

class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def cancel_order(self, order_id: int) -> None:
        order = self.session.get(Order, order_id)
        if order is None:
            raise OrderNotFoundException(order_id)
        if order.status != "PENDING":
            raise ValueError("Only pending orders can be cancelled")
        order.status = "CANCELLED"
        self.session.add(order)
        self.session.commit()
```

**Why correct:** One class, all logic visible, no inheritance or interface indirection. Service accesses the model directly through the SQLModel session — no separate repository layer was added unprompted.

### Incorrect: Python Pass-Through Wrapper

```python
# services/order_service.py — DO NOT create a wrapper that only delegates
class OrderService:
    def cancel_order(self, order_id: int) -> None:
        return self._order_manager.cancel(order_id)
```

**Why incorrect:** The `cancel_order` method is a one-line pass-through that adds no logic. The caller could invoke `order_manager.cancel(order_id)` directly. A wrapper that only delegates obscures the real implementation location and forces readers to chase through an extra file.

### Correct: One LangGraph Per File, No BaseGraph

```python
# graphs/research_assistant.py
from langgraph.graph import StateGraph, END
from app.core.langgraph.state import AgentState
from app.core.langgraph.nodes import call_model, should_continue
from app.core.langgraph.tools import search_tool, fetch_tool
from langgraph.prebuilt import ToolNode

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("agent", call_model)
    g.add_node("tools", ToolNode([search_tool, fetch_tool]))
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    return g.compile()

graph = build_graph()
```

**Why correct:** One compiled `StateGraph` per file. Shared infrastructure (state/nodes/tools) lives in `core/langgraph/`; graph-specific composition stays in this file. No `BaseGraph` ABC.

### Incorrect: Unsolicited BaseGraph

```python
# graphs/base_graph.py — DO NOT CREATE unless user explicitly requests it
from abc import ABC, abstractmethod

class BaseGraph(ABC):
    @abstractmethod
    def build(self):
        ...

class ResearchAssistantGraph(BaseGraph):
    def build(self):
        ...
```

**Why incorrect:** A `BaseGraph` ABC for one or two graph implementations adds a file to jump through and an inheritance layer for no behavioral reason. The compiled graph itself already encapsulates the agent's structure.

### Incorrect: Deep Inheritance Chain

```python
# base/handler.py
class BaseHandler:
    def handle(self, request):
        ...

# orders/cancel_handler.py
class CancelHandler(BaseHandler):
    def handle(self, request):
        ...

# orders/express_cancel_handler.py
class ExpressCancelHandler(CancelHandler):
    def handle(self, request):
        ...
```

**Why incorrect:** A three-level inheritance chain (`ExpressCancelHandler → CancelHandler → BaseHandler`) forces readers to understand all three classes to know what `handle()` actually does. Unless the domain genuinely requires this hierarchy, flatten to one or two concrete classes.

---

## Incorrect: Java Deep Inheritance Chain

```java
// BaseEntity.java
public abstract class BaseEntity { ... }

// BaseOrderEntity.java
public abstract class BaseOrderEntity extends BaseEntity { ... }

// ExpressOrderEntity.java
public class ExpressOrderEntity extends BaseOrderEntity { ... }
```

**Why incorrect:** Three levels of inheritance for an entity class bury the actual fields across multiple files. Prefer a single concrete entity class unless the hierarchy was explicitly requested.
