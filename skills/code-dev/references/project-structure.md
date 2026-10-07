# Project Structure

The directory layouts in this file are **mandatory**, not illustrative. Use them as-is; a project whose current layout differs gets migrated, not exempted. Entries marked `optional` are **prohibited unless the application actually needs them** — that is a restriction, not a style choice. Create only the directories the current project needs, but create those in the shape shown here.

## Java Backend

### Ordinary monolithic Spring project

For a normal single-module Spring Boot application, keep business services under `service/`, and use interface + `impl/`:

```text
com.example.project/
├── controller/
├── dto/
│   ├── request/
│   └── response/
├── service/
│   ├── OrderService.java
│   ├── UserService.java
│   └── impl/
│       ├── OrderServiceImpl.java
│       └── UserServiceImpl.java
├── mapper/
├── entity/
├── config/
└── exception/
```

Responsibilities:

- `controller/` — HTTP boundary: parse/validate request, call service contract, return response.
- `dto/request/` — incoming API models.
- `dto/response/` — outgoing API models.
- `service/` / `services/` — business contracts; implementations live in `impl/`.
- `mapper/` — persistence access when using MyBatis/MyBatis-Plus style mappers.
- `entity/` — persistence models.
- `config/` — framework/infrastructure configuration.
- `exception/` — project/domain exceptions when they have clear ownership.

Use the singular `service/` package name shown above. A project currently using `services/` is migrated to `service/`.

### Multi-Maven / multi-module project with dedicated `*.biz`

When a multi-module Maven project separates business logic into modules such as `community.biz`, the `biz` module owns business contracts and implementations:

```text
middleware-arena-community/
├── community.dto/
├── community.web/
└── community.biz/
    └── src/main/java/com/mware/community/biz/
        ├── favorite/
        │   ├── FavoriteService.java
        │   ├── FavoriteRedisStore.java
        │   ├── FavoriteStreamRelay.java
        │   └── impl/
        │       ├── FavoriteServiceImpl.java
        │       ├── FavoriteRedisStoreImpl.java
        │       └── FavoriteStreamRelayImpl.java
        ├── follow/
        │   ├── FollowService.java
        │   └── impl/
        │       └── FollowServiceImpl.java
        └── like/
            ├── LikeService.java
            ├── LikeRedisStore.java
            ├── LikeStreamRelay.java
            └── impl/
                ├── LikeServiceImpl.java
                ├── LikeRedisStoreImpl.java
                └── LikeStreamRelayImpl.java
```

Rules:

- Interfaces stay in the domain package.
- Implementations stay in that domain package's `impl/`.
- Other packages/modules depend on interface types, not `*Impl`.
- In a dedicated `biz` module, apply this pattern to business-behavior collaborators such as Service, Store, Relay, Manager, Handler, Processor, and adapters.
- DTO/entity/enums/config/exceptions are not forced into interface + impl pairs.

Optional domain-specific packages such as `enums/`, `event/`, `validation/`, or `client/` should be added only when the domain actually needs them.

## Java Microservices

Prefer domain/service ownership over one global shared module:

```text
project-parent/
├── order-service/
├── product-service/
├── user-service/
└── common-api/             # optional; only if the project genuinely needs one
```

The shared module is named `common-api/`. A project currently using `base-service`, `common`, `platform-core`, or `shared-kernel` is migrated to `common-api/`; do not invent other names.

If an individual microservice is a normal Spring module, use its `service/` + `impl/` business structure. If the Maven project instead separates a dedicated `*.biz` module, use the `biz` layout described above.

See `microservice-guidelines.md` for cross-service rules.

## Python Backend (FastAPI + LangGraph)

Use a real Python package under `src/` so imports and the directory tree agree:

```text
src/
└── app/
    ├── __init__.py
    ├── main.py
    ├── api/
    │   └── v1/
    ├── core/
    │   ├── config.py
    │   ├── llm.py
    │   └── middleware.py          # optional
    ├── graphs/
    ├── schemas/
    ├── services/
    ├── models/
    └── memory/                    # optional
```

Do **not** create `utils/`, `common/`, `base/`, or a generic `core/langgraph/` just because they appear in another template. Add them only when the project has a concrete need. A package that already exists is migrated to the layout above rather than kept as-is.

Typical repository-root files:

```text
pyproject.toml
.env.example
tests/
alembic/                 # only when SQL migrations are used
langgraph.json            # only when LangGraph CLI/Studio deployment needs it
```

### `app/main.py`

Creates the `FastAPI` application and registers routers/middleware. Keep business logic out of the entry point.

### `api/`

HTTP route handlers. Organize by API version/domain only when the project is large enough to benefit from it.

Examples:

```text
api/
└── v1/
    ├── chat.py
    └── documents.py
```

A very small service may simply use `api/chat.py`; do not introduce version folders without a requirement.

### `core/`

Infrastructure/configuration used broadly by the application, such as:

```text
core/
├── config.py
├── llm.py
└── middleware.py
```

`core/` is not a dumping ground for business helpers.

### `graphs/`: small LangGraph agent

For a small graph, keep the graph and graph-specific logic together when it remains easy to read:

```text
graphs/
└── research_assistant.py
```

The file may contain its state type, a few nodes, routing functions, and graph composition.

### `graphs/`: complex LangGraph agent

When one graph has several meaningful nodes, use a package owned by that graph:

```text
graphs/
└── research_assistant/
    ├── __init__.py
    ├── graph.py
    ├── state.py
    ├── nodes/
    │   ├── __init__.py
    │   ├── plan.py
    │   ├── retrieve.py
    │   ├── grade_documents.py
    │   └── generate_answer.py
    ├── tools.py                 # switch to tools/ once it holds several substantial tools
    └── prompts.py               # optional; only when prompts are large enough to deserve a file
```

Rules:

- Prefer one primary LangGraph node per node file in a complex graph.
- Small private helpers used only by a node stay with that node.
- Graph-specific `state`, nodes, tools, routing, and prompts stay inside the graph package.
- `nodes/__init__.py` may be empty or contain lightweight imports/`__all__`; no business logic or side effects.
- Do not create a graph package for a graph with only one or two tiny nodes.

### Shared LangGraph infrastructure

Create shared LangGraph infrastructure only after multiple graphs genuinely share the same concern:

```text
core/
└── langgraph/
    ├── checkpoint.py
    ├── common_state.py
    └── common_tools.py
```

Avoid generic names such as `nodes.py` or `graph.py` in shared infrastructure unless their ownership is obvious. Similar-looking graph-specific nodes are not automatically shared nodes.

### `schemas/`

Pydantic request/response/application models. Keep validation with the model or domain that owns it.

### `services/`

Non-agent application/business logic such as database operations, external service calls, document ingestion, or orchestration outside the graph.

Do not introduce a new `repositories/` layer — it is not part of the mandatory layout. If the project already has repositories, services **must** use that boundary rather than bypassing it, because two competing data-access paths are worse than either one alone.

### `models/`

SQLModel/SQLAlchemy persistence models when the application owns relational persistence.

### `memory/`

Optional long-term memory implementations such as pgvector/mem0 adapters. Do not create this package unless the application actually uses long-term memory.

## `__init__.py`

Default rule for application packages:

- It may be empty.
- Use it for lightweight, intentional package-level exports when that improves imports.
- Do not put database connections, model loading, graph compilation, network calls, or other side effects in `__init__.py`.

Example lightweight export:

```python
from .retrieve import retrieve
from .generate_answer import generate_answer

__all__ = ["retrieve", "generate_answer"]
```
