# Project Structure

## Language and application boundaries

The Java/Spring and FastAPI/LangGraph layouts below apply only to those application types, not plain Java tools, other Python applications, TS/JS, C++ or C#. TS/JS follows its framework's entry points and directory conventions; npm packages also follow the package publishing guidelines.

C++ preserves the existing build system and target boundaries: new projects may use `src/` and `tests/`; create `include/` only for externally consumed public headers, keeping private headers near implementations. C# preserves solution/project boundaries: organize `.csproj` and test projects by application type, and follow the entry-point conventions of ASP.NET Core, desktop applications or libraries. Do not split projects merely to standardize a directory tree or apply Java's `service/impl/` pattern. See [configuration guidelines](configuration-guidelines.md) for formats and environment layouts.

Layer responsibilities and applicable naming rules are mandatory; example trees show their intended organization, not a requirement to create every illustrated file. Create only needed directories. Correct affected structure within the task's scope, and report unrelated debt instead of automatically migrating the whole project. Entries marked `optional` are prohibited unless actually needed.

Before reorganizing, identify the application type, existing framework boundaries and actual domains. Prefer one consistent organization per application: layer-first with domain subdivisions, or an existing domain-first layout containing the same responsibilities. Do not introduce a competing root layout merely to resemble an example. A package name or file suffix is not evidence of layer ownership.

## Cross-language ownership decisions

Apply these responsibilities using the project's native names, not a universal `schemas/` directory:

| Responsibility | Ownership |
|---|---|
| Persistence entity / ORM mapping | Persistence layer: Java entities, Python models, TS ORM models, C# EF entities; C++ persistence mappings only when present |
| Transport request/response or service boundary DTO | Contract/schema/DTO owner, grouped by domain and role; keep separate from persistence entities |
| Internal domain value object / state / invariant | Owning domain, not automatically an HTTP DTO or database model |
| Business orchestration | Domain service/application owner |
| External client, storage or messaging implementation | Existing infrastructure/integration owner; create an adapter only for a real boundary |
| Application startup and dependency wiring | Composition/lifecycle entry point |

C# `Models` and TS `models` may be ambiguous: inspect persistence attributes/mappings, serialization and callers rather than assuming every type belongs there. Browser TS types must not import server persistence implementations. C++ public headers belong in the public include tree only when they are part of the supported external API; private DTOs/helpers remain with their owning target/domain. Do not expose an internal type merely to fit a directory template.

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
- `service/` — business contracts; implementations live in `impl/`.
- `mapper/` — persistence access when using MyBatis/MyBatis-Plus style mappers.
- `entity/` — persistence models.
- `config/` — framework/infrastructure configuration.
- `exception/` — project/domain exceptions when they have clear ownership.

Use the singular `service/` package name shown above. A project currently using `services/` is migrated to `service/`.

When several domains or substantial modules exist, subdivide the relevant layer by domain rather than accumulating unrelated files: for example `controller/order/`, `dto/request/order/`, `dto/response/order/`, `service/order/impl/`, `mapper/order/` and `entity/order/`. A cohesive single-domain module may keep a shallow layout. Existing domain-first layouts may place these responsibilities under `order/`; preserve that consistent ownership rather than adding a second layout. The business interface and implementation remain paired under their owner.

Create `mapper/` only when the project uses mapper-based persistence. A JPA or other persistence framework keeps its actual repository/access boundary instead of adding MyBatis-shaped packages. No persistence layer is required for an application without persistence. DTOs, entities, enums and configuration remain distinct responsibilities; do not place them together just because a service uses them.

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

For a new shared API/event contract module, use `common-api/` unless project conventions specify otherwise. Do not rename `common`, `platform-core`, `shared-kernel` or another existing module merely because it is shared: inspect its contents and consumers first. Infrastructure implementation and domain logic do not become API contracts through renaming. A module migration needs a task-related reason and updates to all affected dependencies.

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
    │   └── v1/                    # optional; only when API versioning exists
    ├── core/
    │   ├── config.py
    │   ├── llm.py                 # optional; only when LLM integration exists
    │   └── middleware.py          # optional
    ├── graphs/                    # optional; only when graph workflows exist
    ├── schemas/
    ├── services/
    ├── models/                    # optional; only when persistence mappings exist
    └── memory/                    # optional
```

Do **not** create `utils/`, `common/`, `base/`, or a generic `core/langgraph/` just because they appear in another template. Add them only for a concrete need. Apply structural corrections to the affected domain within the authorized scope.

Typical repository-root files:

```text
pyproject.toml
.env.example             # only when using dotenv; otherwise provide the chosen format's example
tests/
alembic/                 # only when SQL migrations are used
langgraph.json            # only when LangGraph CLI/Studio deployment needs it
```

### `app/main.py`

Creates the `FastAPI` application and registers routers/middleware. Keep business logic out of the entry point.

### `api/`

For version introduction, coexistence, DTO ownership, deployment and retirement, follow [API versioning guidelines](api-versioning-guidelines.md). Do not rename `v1/` to `v2/` as a substitute for a compatibility migration.

HTTP route handlers. Organize by API version/domain only when the project is large enough to benefit from it.

Without API versioning, apply the same domain rules directly under `api/`, such as `api/reminder/`. Version directories never replace domain ownership.

When multiple API domains exist, group routes by their actual domain instead of accumulating unrelated endpoints in one router or flattening every route file under `api/`. Within an existing version boundary, use domain packages such as `api/v1/reminder/` when that domain has multiple route modules. A single cohesive domain router may remain `api/v1/reminder.py`. Preserve the project's versioning contract; do not invent `v1/` or split routes mechanically by HTTP method. Router registration stays at the application or API composition boundary; route modules handle HTTP concerns, not persistence models, DTO definitions or scheduling logic.

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

Boundary data belongs here, including service input/output structures and read-only result DTOs, even when they are dataclasses or plain data types rather than Pydantic models. Being returned by one service does not justify placing a boundary DTO beside that service. `BaseModel`, `dataclass` and a name ending in `Model` alone do not establish persistence ownership.

**Group schemas by domain, then separate actual data roles.** When several domains exist, use packages such as `schemas/reminder/` and `schemas/pay/` rather than flattening unrelated types under `schemas/`. Within a domain, separate HTTP request and response types into `request.py` and `response.py` (or `request/` and `response/` packages when multiple substantial modules exist), similar to Java's DTO request/response distinction. Name request types by operation, such as `CreateReminderRequest` and `UpdateReminderRequest`; response types describe returned data. Do not reuse one persistence-shaped type for create, update and response solely because fields overlap.

Service-only input/output structures may use `input.py` and `output.py` when they have distinct contracts from HTTP DTOs; shared domain boundary types may use a purpose-specific module. Do not label internal service data as an HTTP request or response merely for symmetry, duplicate equivalent DTOs without a contract difference, or create empty role directories. A small domain with only one cohesive schema module may initially use `schemas/reminder.py`; split when independent roles emerge.

For a domain with distinct HTTP request/response contracts and multiple route responsibilities, the relevant parts may look like this:

```text
app/
├── api/
│   └── v1/                       # only when versioning exists
│       └── reminder/
│           ├── __init__.py
│           ├── task_routes.py
│           └── subscription_routes.py
├── schemas/
│   └── reminder/
│       ├── __init__.py
│       ├── request.py
│       └── response.py
├── models/
│   └── reminder.py               # database mapping
└── services/
    └── reminder/
        ├── __init__.py
        ├── reminder_service.py
        └── scheduler.py
```

Apply the same domain-ownership principle to `models/` when several domains or multiple persistence modules require it. Each layer retains its own responsibility; matching domain names across layers do not require matching file counts or empty packages. Update imports and router registration when reorganizing, and verify that route paths and request/response contracts are preserved.

### `services/`

Non-agent application/business logic such as database operations, external service calls, document ingestion, or orchestration outside the graph.

**Organize subpackages by business domain; do not keep all business files flat under `services/`.** When multiple independent domains exist, or one domain has multiple modules with distinct responsibilities, create meaningful subpackages such as `services/pay/` and `services/order/`. Keep each domain's implementations and private collaborators together.

For example, use this layout when payment and refund logic exist; create the illustrated directories only for actual responsibilities:

```text
services/
├── __init__.py
├── pay/
│   ├── __init__.py
│   ├── payment_service.py
│   └── refund_service.py
└── order/
    ├── __init__.py
    └── order_service.py
```

A small project with a single domain and few modules may initially use a simple layout such as `services/order_service.py`. Once the domain boundaries above emerge, organize by domain rather than waiting for files to accumulate. Do not split by arbitrary file counts, create empty domain packages, or introduce interfaces, forwarding layers or Java-style `impl/` merely for packaging. Update imports, dependency providers and test references when moving modules; keep `__init__.py` lightweight and free of business logic or startup side effects.

Do not add `repositories/` for template completeness or trivial forwarding. Introduce it only for a real persistence boundary, stable shared query responsibility, replacement requirement or explicit user request. Reuse existing boundaries and avoid competing access paths for the same responsibility; see [Python guidelines](python-guidelines.md#services-and-persistence).

### Dependency direction and composition

API handlers call service entry points and exchange schema types. Services may use schemas and the existing persistence/integration boundary, but must not import API routers or HTTP-specific exceptions. Persistence definitions must not depend on API or service implementations; schemas must not import these implementations to define their shape. Shared enums or value types need a real domain owner, not a circular import or a new generic `common/` package.

Keep application creation, router registration, dependency-provider wiring and job startup at the composition/lifecycle boundary. A domain scheduler may live beside its service, but importing the package must not start it. Keep tests separate from runtime application modules and group them by the affected domain or boundary without requiring a test file for every source file.

Do not keep both `reminder.py` and a `reminder/` package under the same parent as competing owners. When converting a module to a package, update references and remove the obsolete owner after checking usages. A structure change must preserve public imports or explicitly account for their compatibility, router registrations and resource/migration discovery.

### `models/`

SQLModel/SQLAlchemy persistence models when the application owns relational persistence.

Reserve this layer for actual persistence definitions and mappings. Inspect table/mapping declarations and database usage rather than inferring ownership from the word "model". A read-only service result is not a database model merely because it contains fields loaded from a table.

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
