# Project Structure

Directory layouts in this file are **starting points, not mandatory scaffolds**. Preserve an existing project's structure when it is coherent. Create only directories needed by the current project.

## Java Backend

A common Spring backend shape is:

```text
com.example.project
├── controller
├── dto
│   ├── request
│   └── response
├── service
├── mapper
├── entity
├── config
└── exception
```

Optional domain-specific packages such as `enums/`, `event/`, `validation/`, or `client/` should be added only when the domain actually needs them.

### Responsibilities

- `controller/` — HTTP boundary: parse/validate request, call application/service logic, return response.
- `dto/request/` — incoming API models.
- `dto/response/` — outgoing API models.
- `service/` — business/application logic.
- `mapper/` — persistence access when using MyBatis/MyBatis-Plus style mappers.
- `entity/` — persistence models.
- `config/` — framework/infrastructure configuration.
- `exception/` — project/domain exceptions when they have clear ownership.

Do not create every package just because it appears in this example.

## Java Microservices

Prefer domain/service ownership over one global shared module:

```text
project-parent/
├── order-service/
├── product-service/
├── user-service/
└── shared-module/          # optional; only if the project genuinely needs one
```

The shared module may already be named `base-service`, `common`, `common-api`, `platform-core`, etc. Follow the repository's existing name instead of inventing or renaming it.

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

Do **not** create `utils/`, `common/`, `base/`, `repositories/`, or a generic `core/langgraph/` just because they appear in another template. Add them only when the project has a concrete need or already uses that convention.

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
    ├── tools.py                 # or tools/ when there are several substantial tools
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

Do not introduce a new `repositories/` layer by default. If the existing project already has repositories, use them consistently rather than bypassing them.

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
