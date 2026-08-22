# Python Guidelines

Target context: Python backend, especially **FastAPI + LangGraph**. Existing project conventions take precedence over these defaults.

See `project-structure.md` before creating or moving packages.

## FastAPI boundaries

Keep HTTP-specific behavior at the API layer:

```python
@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: int, service: OrderService = Depends(get_order_service)):
    order = service.cancel_order(order_id)
    return OrderResponse.model_validate(order)
```

Prefer:

```text
API/router
→ parse HTTP input / Depends / response model / HTTP error mapping

service
→ business rules and application orchestration

model / mapper / repository (if the project has one)
→ persistence
```

Do not raise `HTTPException` deep inside domain/service code unless the existing project intentionally couples that layer to FastAPI.

## Sync vs async

Use `async def` when the function actually awaits asynchronous I/O.

Do not call slow blocking HTTP/database/file APIs directly from an async request or LangGraph node and assume `async` makes them non-blocking. Use the async client supported by the dependency, or follow the project's established thread/offload pattern.

Do not convert an entire code path to async only for style consistency.

## Services and persistence

For a small project with one implementation, a plain class or module-level function is enough:

```python
class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def cancel_order(self, order_id: int) -> Order:
        order = self.session.get(Order, order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        if order.status != "PENDING":
            raise OrderStateError("Only pending orders can be cancelled")

        order.status = "CANCELLED"
        self.session.add(order)
        self.session.commit()
        return order
```

Do not create an ABC/Protocol solely because there is one implementation.

Do not introduce a new `repositories/` layer automatically. If the project already uses repositories, preserve that boundary and do not bypass it.

## Pydantic schemas

Use Pydantic models for external request/response data:

```python
class CreateOrderRequest(BaseModel):
    product_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)
```

Prefer `Field`, `field_validator`, and `model_validator` over a custom generic validation framework.

Do not return ORM objects directly from public APIs unless response serialization is deliberately configured and already used by the project.

Duplicated fields between create/update schemas are acceptable when the schemas have different API meanings.

## Dependency injection

Use FastAPI `Depends` for request-scoped dependencies and infrastructure wiring when appropriate. Do not create a custom DI container just to wrap `Depends`.

Keep dependency provider functions small and explicit:

```python
def get_order_service(session: Session = Depends(get_session)) -> OrderService:
    return OrderService(session)
```

A provider like this is a legitimate framework boundary; do not classify it as a meaningless pass-through wrapper.

## LangGraph: ownership first

Each graph owns its graph-specific state, nodes, tools, prompts, and routing logic.

Only move something to shared `core/langgraph/` after multiple graphs genuinely use the same concern.

### Small graph

When the complete flow remains readable, one file is fine:

```python
# app/graphs/research_assistant.py
class AgentState(TypedDict):
    query: str
    documents: list[str]
    answer: str


def retrieve(state: AgentState) -> dict:
    documents = retriever.invoke(state["query"])
    return {"documents": documents}


def generate_answer(state: AgentState) -> dict:
    answer = model.invoke(...)
    return {"answer": answer}


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("retrieve", retrieve)
    builder.add_node("generate_answer", generate_answer)
    builder.add_edge("retrieve", "generate_answer")
    return builder.compile()


graph = build_graph()
```

### Complex graph

When several meaningful nodes make one file hard to scan, split by node:

```text
graphs/research_assistant/
├── __init__.py
├── graph.py
├── state.py
├── nodes/
│   ├── __init__.py
│   ├── plan.py
│   ├── retrieve.py
│   ├── grade_documents.py
│   └── generate_answer.py
├── tools.py
└── prompts.py              # optional
```

Prefer one primary node per file. Small helpers used only by that node stay in the same file.

`nodes/__init__.py` may remain empty or expose node functions:

```python
from .generate_answer import generate_answer
from .retrieve import retrieve

__all__ = ["retrieve", "generate_answer"]
```

Do not put graph compilation, model initialization, network calls, or other side effects in `__init__.py`.

## LangGraph node rules

A node should make its state contract obvious:

```python
def retrieve(state: AgentState) -> dict:
    documents = retriever.invoke(state["query"])
    return {"documents": documents}
```

Prefer returning the state updates owned by the node instead of mutating unrelated state fields in place.

Keep routing functions focused on routing decisions:

```python
def route_after_grade(state: AgentState) -> Literal["rewrite", "generate"]:
    return "generate" if state["documents_relevant"] else "rewrite"
```

Do not hide substantial business work inside a conditional-edge routing function.

## LangGraph tools vs nodes

A **tool** is an externally callable capability exposed to the model or ToolNode. A **node** is a graph execution step.

Do not mark every node with `@tool`, and do not turn a normal service function into a tool unless the model actually needs permission to select/call it.

Graph-specific tools stay with the graph. Truly cross-agent tools may move to shared infrastructure.

## Graph construction and compilation

Keep graph wiring in `graph.py` (or the single graph file):

```python
def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)
    ...
    return builder.compile(checkpointer=checkpointer)
```

Avoid compiling graphs as an import side effect inside package `__init__.py`.

A module-level compiled `graph` is acceptable when the runtime/framework expects it and initialization is cheap/configured. If construction depends on request-specific dependencies, credentials, tenant state, or runtime configuration, use an explicit factory instead.

## Checkpointing and persistence

Checkpoint/memory configuration belongs at graph/runtime composition boundaries, not inside arbitrary nodes.

Keep these concepts separate:

- graph state: data flowing through the current execution
- checkpointer: persistence for graph execution/thread state
- long-term memory/store: cross-thread or durable application memory

Do not create a `memory/` package unless the application actually uses long-term memory.

## Prompts

Short prompts used by one node may stay next to that node. Move prompts to `prompts.py` or a prompt package only when they are long, reused, versioned, or independently tested.

Do not create a generic prompt registry for a few static strings.

## Errors and retries

Retry transient infrastructure failures at the boundary that owns the call. Do not wrap every node in a generic retry decorator without knowing which failures are retryable.

Keep business rejection separate from transient failure. For example, "document is irrelevant" is routing/business state, not an exception that should be blindly retried.

## Repeated code and abstractions

Do not extract shared validators, nodes, state bases, tool bases, or `BaseGraph` merely because two implementations look similar.

Extraction is reasonable when there is a concrete shared invariant/contract, an existing project abstraction, multiple implementations, or an explicit user request.

Avoid proactive:

- `BaseGraph`, `BaseState`, `BaseAgent`
- generic `common/`, `utils/`, `helpers/` packages
- custom DI containers
- pass-through manager/service layers
- repository layers that the project does not already use

## `__init__.py`

Default to empty application-package `__init__.py` files unless a package-level API is useful.

Good:

```python
from .retrieve import retrieve

__all__ = ["retrieve"]
```

Avoid side effects such as:

```python
# do not do this in __init__.py
model = load_large_model()
graph = build_graph().compile()
database.connect()
```
