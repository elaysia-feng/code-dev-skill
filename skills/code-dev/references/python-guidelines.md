# Python Guidelines

Target context: Python backend, especially **FastAPI + LangGraph**. These are **mandatory** rules within the authorized task scope. Correct affected code and report unrelated structural debt rather than migrating it automatically. Explicit user requirements and applicable project/company standards take precedence; see [`../SKILL.md`](../SKILL.md).

既有结构调整遵循 [`../SKILL.md`](../SKILL.md) 的“既有项目迁移”规则；已有会话授权或明确任务范围时直接执行，不重复询问。

Structure is defined in [`project-structure.md`](project-structure.md) and is mandatory there too.

## File ownership before implementation

Before creating or moving a type, inspect its definition, framework markers, callers, serialization and persistence usage, and the project's layer conventions. Classify by responsibility, not its name or convenience of placing it next to a service:

| Responsibility | Placement in the backend layout |
|---|---|
| Database table or ORM mapping | `models/<domain>.py` |
| Request, response, service input/output DTO or read-only result structure | `schemas/<domain>.py` for a small cohesive module, otherwise `schemas/<domain>/` with role-specific modules |
| Business rules, application orchestration or domain scheduling | `services/<domain>/` |
| Graph-specific state | The owning graph's `state.py`, following the graph layout |
| Private implementation helper or internal domain value object | Its existing owner; do not move it to `schemas/` solely because it holds data |

For example, a `ReminderTask` mapped to a database table belongs in `models/reminder.py`, a read-only `Reminder` returned by the service belongs in the reminder schema module (or the appropriate response/output module when roles are split), and reminder logic and scheduling belong in `services/reminder/`. Do not create `services/reminder/reminder_model.py` to hold that output DTO. Names and field mutability alone do not determine the layer.

Schemas must not import services or persistence models merely to define their data shape. Perform conversion at the appropriate business/API boundary instead of creating circular imports or returning ORM objects as DTOs. Preserve existing public identifiers unless renaming is authorized.

When evidence leaves materially different valid placements, describe the alternatives and ask before creating the file. Do not invent a new layer or use "it runs" as justification. After relocation, update imports, public exports, dependency providers and tests; verify the affected import path and behavior. Import validation alone does not prove database access or scheduling works. During review, report misplaced types rather than moving them automatically.

## FastAPI boundaries

API versions follow [API versioning guidelines](api-versioning-guidelines.md): preserve required old contracts, add only necessary version-specific routes and DTOs, and reuse business/persistence layers where semantics remain the same.

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

Never raise `HTTPException` in domain/service code. Map HTTP errors at the router boundary; a service that already raises it needs the calls below it converted.

## Sync vs async

Use `async def` when the function actually awaits asynchronous I/O.

Do not call slow blocking HTTP/database/file APIs directly from an async request or LangGraph node and assume `async` makes them non-blocking. Use the async client supported by the dependency, or follow the project's established thread/offload pattern.

Do not convert an entire code path to async only for style consistency.

## Services and persistence

Organize `services/` into subpackages as real business boundaries emerge, such as `services/pay/`. Multiple domains or multiple responsibility-specific modules within a domain must not remain flat at the root. See [`project-structure.md`](project-structure.md#services) for layouts and small-project boundaries. Packaging does not imply adding ABC/Protocol, interface/implementation pairs or forwarding layers.

For a small project with one implementation, a plain class or module-level function is enough:

```python
class OrderService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def cancel_order(self, order_id: int) -> Order:
        order = self.session.get(Order, order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        if order.status != OrderStatus.PENDING:
            raise OrderStateError("Only pending orders can be cancelled")

        order.status = OrderStatus.CANCELLED
        self.session.add(order)
        self.session.flush()  # 事务提交由公开业务入口统一管理。
        return order
```

Do not create an ABC/Protocol solely because there is one implementation.

The example assumes `OrderStatus` is the domain-owned enum and an outer public business entry point owns the transaction; this example only shows the business checks and flush, not transaction begin/commit/rollback. It illustrates service ownership, not concurrency safety: when competing writes are possible, follow [runtime boundaries](runtime-boundaries.md) for conditional updates and transaction ownership.

Do not add `repositories/` merely to complete a template or forward one ORM call. A real persistence contract, replaceable backend, stable shared query responsibility or explicit user request can justify it. Reuse the existing access boundary and migrate affected callers consistently; do not maintain competing direct-ORM and repository paths for the same responsibility.

事务由公开业务入口统一管理；参与同一操作的 services/repository 不各自提交。查询通常无需额外事务包装；避免在事务中等待 LLM、网络调用等慢操作。提交、回滚和资源释放采用项目所用数据库库的机制，并验证失败时能正确回滚。


## Pydantic schemas

Organize schemas by business domain and actual data role, separating request and response contracts when they differ. Organize API routers by domain under any existing version boundary. Follow the package and small-project rules in [`project-structure.md`](project-structure.md#schemas); do not flatten unrelated schemas/routes or add empty packages for symmetry.

Use Pydantic models for external request/response data:

```python
class CreateOrderRequest(BaseModel):
    product_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)
```

Prefer `Field`, `field_validator`, and `model_validator` over a custom generic validation framework.

Do not return ORM objects directly from public APIs. Always return `schemas/` models via `response_model`.

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

Extraction is reasonable when there is a concrete shared invariant/contract, multiple implementations, an explicit extension point, or an explicit user request. An existing project abstraction is **not** by itself a reason to extract — that is what produces speculative layering.

Avoid proactive:

- `BaseGraph`, `BaseState`, `BaseAgent`
- generic `common/`, `utils/`, `helpers/` packages
- custom DI containers
- pass-through manager/service layers
- repository layers without a concrete persistence boundary

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
