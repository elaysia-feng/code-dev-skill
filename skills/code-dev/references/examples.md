# Examples

These examples illustrate the decision rule: preserve real boundaries and existing conventions; avoid indirection that exists only for symmetry or line-count reduction.

## Java monolith: service interface + impl

For an ordinary monolithic Spring project, business services use a contract plus implementation:

```text
service/
├── OrderService.java
└── impl/
    └── OrderServiceImpl.java
```

```java
public interface OrderService {
    void cancelOrder(Long orderId);
}
```

```java
@Service
public class OrderServiceImpl implements OrderService {

    @Override
    public void cancelOrder(Long orderId) {
        OrderEntity order = orderMapper.selectById(orderId);
        if (order == null) {
            throw new OrderNotFoundException(orderId);
        }
        if (order.getStatus() != OrderStatus.PENDING) {
            throw new IllegalStateException("Only pending orders can be cancelled");
        }

        order.setStatus(OrderStatus.CANCELLED);
        orderMapper.updateById(order);
    }
}
```

Callers inject `OrderService`, not `OrderServiceImpl`.

## Java multi-module: dedicated `biz` module

For a multi-Maven project with a dedicated business module, organize each domain inside `biz` with contracts and `impl/`:

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

Here the interface-first rule applies not only to `Service`, but to business-behavior collaborators inside `biz` such as Store/Relay/Manager/Handler when they represent replaceable business contracts.

Do not apply the same rule to `LikeStatus` enum, DTOs, entities, configuration classes, or exceptions.

## Java: domain enum is not over-abstraction

Good:

```java
public enum OrderStatus {
    PENDING,
    PAID,
    CANCELLED
}
```

Bad ownership:

```text
common/
└── CommonEnums.java   # unrelated enums from many domains collected together
```

The problem is the dumping-ground ownership, not the use of an enum.

## Java: repeated validation

Two similar checks do not automatically justify a shared validator:

```java
if (quantity == null || quantity <= 0) {
    throw new IllegalArgumentException("quantity must be greater than 0");
}
```

If several callers must obey the exact same security/signature rule and inconsistent fixes have caused defects, a dedicated shared component can be better:

```text
security/
└── RequestSignatureValidator.java
```

The abstraction is justified by a stable shared invariant, not by duplicated lines.

## Thin boundary: keep when it owns behavior

This is not a meaningless wrapper:

```java
public interface OrderService {
    void cancelOrder(Long orderId);
}
```

```java
@Service
public class OrderServiceImpl implements OrderService {

    @Override
    @Transactional
    @PreAuthorize("hasAuthority('ORDER_CANCEL')")
    public void cancelOrder(Long orderId) {
        orderManager.cancel(orderId);
    }
}
```

The implementation owns the project-required business contract plus transaction/security boundaries even though the body is short.

An extra wrapper with no new policy or boundary is still suspicious:

```text
OrderService -> OrderServiceImpl -> OrderServiceDelegate -> OrderManager
```

when `OrderServiceDelegate` only forwards the call.

## Python: FastAPI schema validation

Good:

```python
class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
```

Avoid inventing a generic validator framework for simple request-model constraints.

## Python: preserve an existing repository layer

If the project already has:

```text
repositories/
├── order_repository.py
└── user_repository.py
```

then a new service should use that boundary rather than bypass it just because a greenfield project might access SQLAlchemy directly.

## Python: async does not make blocking I/O async

Bad:

```python
@router.get("/profile")
async def profile():
    response = requests.get(EXTERNAL_URL)
    return response.json()
```

Prefer the project's asynchronous HTTP client:

```python
@router.get("/profile")
async def profile(client: httpx.AsyncClient = Depends(get_http_client)):
    response = await client.get(EXTERNAL_URL)
    return response.json()
```

## LangGraph: small graph stays small

A two-node graph may remain one file:

```python
class AgentState(TypedDict):
    query: str
    documents: list[str]
    answer: str


def retrieve(state: AgentState) -> dict:
    return {"documents": retriever.invoke(state["query"])}


def generate_answer(state: AgentState) -> dict:
    return {"answer": model.invoke(...) }


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("retrieve", retrieve)
    builder.add_node("generate_answer", generate_answer)
    builder.add_edge("retrieve", "generate_answer")
    return builder.compile()
```

Do not create five files merely because LangGraph has named nodes.

## LangGraph: complex graph splits by node

When the graph contains several substantial nodes:

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
└── tools.py
```

`nodes/retrieve.py`:

```python
def retrieve(state: AgentState) -> dict:
    documents = retriever.invoke(state["query"])
    return {"documents": documents}
```

`nodes/__init__.py` may expose only lightweight names:

```python
from .generate_answer import generate_answer
from .retrieve import retrieve

__all__ = ["retrieve", "generate_answer"]
```

Do not initialize models, connect databases, or compile graphs in `__init__.py`.

## LangGraph: node vs tool

Node:

```python
def retrieve(state: AgentState) -> dict:
    ...
```

Tool selected/called by the model:

```python
@tool
def search_web(query: str) -> str:
    ...
```

A graph node does not become a tool merely because both are callable Python functions.

## LangGraph: routing stays routing

Good:

```python
def route_after_grade(state: AgentState) -> Literal["rewrite", "generate"]:
    return "generate" if state["documents_relevant"] else "rewrite"
```

Avoid hiding LLM/database work inside the routing function; put that work in a node and route from the resulting state.

## Microservice: shared contract with clear ownership

Good when several services use the same event schema:

```text
common-api/
└── event/
    └── OrderCreatedEvent.java
```

Bad:

```text
base-service/
├── OrderValidator.java
├── ProductValidator.java
└── UserBusinessHelper.java
```

when those classes contain independent domain business rules. A shared module should own shared contracts/infrastructure, not become a place to move unrelated business code.
