# Project Structure

<<<<<<< HEAD
本文目录规范适用于新增代码、目录和模块；既有项目的全量迁移必须先按 [`../SKILL.md`](../SKILL.md) 的“既有项目迁移”规则询问用户。用户同意后全量迁移；不同意则保留既有结构，仅新增部分遵循本规范。标记 `optional` 的目录仅在应用确有需要时创建，不照搬空目录模板。
=======
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
>>>>>>> 3af7b9d92fb5a5e0df3955aa6c8af7b97ce5764f

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

新增包使用上述单数名称 `service/`。既有 `services/` 仅在用户同意全量迁移后改为 `service/`。

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

<<<<<<< HEAD
新建共享模块使用 `common-api/`。既有 `base-service`、`common`、`platform-core` 或 `shared-kernel` 仅在用户同意全量迁移后改为 `common-api/`；不同意时保留并复用已有模块，不另建重复模块。
=======
For a new shared API/event contract module, use `common-api/` unless project conventions specify otherwise. Do not rename `common`, `platform-core`, `shared-kernel` or another existing module merely because it is shared: inspect its contents and consumers first. Infrastructure implementation and domain logic do not become API contracts through renaming. A module migration needs a task-related reason and updates to all affected dependencies.
>>>>>>> 3af7b9d92fb5a5e0df3955aa6c8af7b97ce5764f

If an individual microservice is a normal Spring module, use its `service/` + `impl/` business structure. If the Maven project instead separates a dedicated `*.biz` module, use the `biz` layout described above.

See `microservice-guidelines.md` for cross-service rules.

## Python Backend (FastAPI + LangGraph)

新建后端默认使用 `src/app/` 包布局，配置包发现、开发安装及启动入口，验证从不同工作目录也能正常导入；不要仅搬文件后依赖临时修改 `sys.path`。已有 `app/` 平铺布局的调整受迁移选择约束。

```text
src/
└── app/
    ├── __init__.py
    ├── main.py
    ├── api/
<<<<<<< HEAD
    │   └── v1/                    # optional; API 确需版本化时创建
    ├── core/
    │   ├── config.py
    │   ├── llm.py                 # optional; 使用 LLM 时创建
    │   └── middleware.py          # optional
    ├── graphs/                    # optional; 使用 LangGraph 时创建
    ├── schemas/
    ├── services/
    ├── models/                    # optional; 拥有数据库模型时创建
    ├── repositories/              # optional; 有明确数据访问边界时创建
    └── memory/                    # optional
```

Do **not** create `utils/`, `common/`, `base/`, or a generic `core/langgraph/` just because they appear in another template. Add them only when the project has a concrete need. 既有包仅在用户同意全量迁移后调整到上述布局。
=======
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
>>>>>>> 3af7b9d92fb5a5e0df3955aa6c8af7b97ce5764f

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

<<<<<<< HEAD
小项目可以由 service 直接进行简单数据库访问。有复用查询、复杂持久化规则、存储替换或需要隔离测试的明确边界时，可新增 `repositories/`；不要为单次 CRUD 添加纯转发层。已有 repository 时必须复用该边界，不能另建并行数据访问路径。事务由业务入口管理，repository 不自行提交会拆散同一业务操作的事务。
=======
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
>>>>>>> 3af7b9d92fb5a5e0df3955aa6c8af7b97ce5764f

### `models/`

SQLModel/SQLAlchemy persistence models when the application owns relational persistence.

Reserve this layer for actual persistence definitions and mappings. Inspect table/mapping declarations and database usage rather than inferring ownership from the word "model". A read-only service result is not a database model merely because it contains fields loaded from a table.

### `memory/`

Optional long-term memory implementations such as pgvector/mem0 adapters. Do not create this package unless the application actually uses long-term memory.

## TypeScript 前端应用

以下为无强制文件路由的 React/Vue 应用基线，按实际需要创建目录；Next.js 等框架使用其 `app/`、`pages/` 等保留目录，不能照搬 `pages/` 的含义。具体职责见 [frontend-guidelines.md](frontend-guidelines.md)。

```text
src/
├── main.ts / main.tsx      # 使用框架实际入口，不同时创建两套
├── App.vue / App.tsx       # 应用组合入口
├── pages/                 # 路由页面
├── features/              # optional; 较复杂业务按功能归属组织
│   └── orders/
│       ├── components/
│       ├── api.ts
│       ├── types.ts
│       └── useOrders.ts   # optional; React hook 或 Vue composable
├── components/            # optional; 跨功能通用组件
├── api/                   # optional; 共享请求客户端和协议处理
├── router/                # optional; 框架需要显式路由配置时创建
├── stores/                # optional; 确有共享状态时创建
├── assets/                # optional; 参与构建的资源
└── styles/                # optional; 全局样式和设计变量
```

小页面可直接组织在页面文件及相邻模块中；功能变复杂时再聚合到 `features/<功能>/`。功能内部不得直接依赖其他功能的私有组件；共享内容须有明确契约。不要同时在全局与功能目录中维护两套请求、状态或类型。既有结构迁移仍须先询问用户。

## Python 布局参考

- [PyPA：src 与平铺布局](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)：两种布局有不同的安装与导入行为，`src/` 需要配套安装配置。
- [FastAPI：多文件应用](https://fastapi.tiangolo.com/tutorial/bigger-applications/)：按职责组织包并组合路由；本规范的具体目录命名属于项目约定。

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
