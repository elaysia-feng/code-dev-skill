# Python Guidelines

Target stack: **FastAPI + LangGraph**. See `references/project-structure.md` for the directory layout these guidelines assume.

## Service

When there is only one implementation, prefer a plain class or module-level functions:

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

Do **not** automatically create abstract base classes (ABCs) for services unless multiple implementations exist or the user explicitly requests them.

Do **not** proactively create `Protocol` classes for type hints. Use concrete types or simple type aliases instead. Protocols add indirection that obscures the real implementation without improving readability.

Do **not** introduce a separate `repositories/` layer — services talk to `models/` directly via the SQLModel/SQLAlchemy session.

## Schemas

Use Pydantic models for request/response data, placed under `schemas/`:

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

Each schema owns its own validation (field validators or `model_validator`). Duplicated field declarations across schemas are allowed.

Do not return database entities directly from controllers or public API endpoints.

## Graphs (LangGraph)

One compiled `StateGraph` per file under `graphs/`. Each graph file imports its state, nodes, and tools from `core/langgraph/` and exports a compiled `graph`:

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

Rules:
- Do **not** create a `BaseGraph` ABC or abstract graph builder.
- Do **not** extract shared cross-graph state into a generic `BaseState` unless the user asks.
- Cross-graph nodes/tools live in `core/langgraph/`. Graph-specific nodes/tools stay in the graph file.

## Repeated Code

Duplicated validation is allowed. Each schema owns its own validation. Duplicated node logic across graph files is allowed. Do not extract a shared validator, shared node, or shared `BaseGraph` unless the user asks.

**Do not proactively create:**

- `common/validators.py`
- `BaseModel` with a shared abstract `validate()`
- `ValidationMixin`
- `shared/exceptions.py` (unless multiple modules genuinely share the same exception types)
- `graphs/base_graph.py` or `graphs/abstract_graph.py`

## Forbidden Proactive Refactorings

When implementing a feature, do **not**:

- Extract shared functions or mixins
- Create `common/` or `util/` packages
- Create abstract base classes
- Create shared DTOs or shared services
- Merge similar functions
- Introduce decorator-based validation unless the user requests it
- Apply design patterns the user did not ask for
- Split a readable single-module implementation across many files
- Modify unrelated module structure
- Create a `BaseGraph` / `BaseState` / `BaseAgent` for LangGraph
- Move graph-specific nodes or tools into `core/langgraph/` on your own

User says "implement feature" → implement only that feature. User says "refactor" → then refactor.

## Pass-Through Methods

A function or method that only delegates to another callable without adding logic is a pass-through wrapper. Do not create these unless explicitly requested:

```python
# services/order_service.py — DO NOT create a wrapper that only delegates
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
| Cross-graph LangGraph nodes/tools/state | `core/langgraph/` |

Only extract what the user specified. Keep the extraction minimal.