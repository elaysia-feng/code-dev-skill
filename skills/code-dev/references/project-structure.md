# Project Structure

## Language and application boundaries

The Java/Spring and FastAPI/LangGraph layouts below apply only to those application types, not plain Java tools, other Python applications, TS/JS, C++ or C#. TS/JS follows its framework's entry points and directory conventions; npm packages also follow the package publishing guidelines.

C++ preserves the existing build system and target boundaries: new projects may use `src/` and `tests/`; create `include/` only for externally consumed public headers, keeping private headers near implementations. C# preserves solution/project boundaries: organize `.csproj` and test projects by application type, and follow the entry-point conventions of ASP.NET Core, desktop applications or libraries. Do not split projects merely to standardize a directory tree or apply Java's `service/impl/` pattern. See [configuration guidelines](configuration-guidelines.md) for formats and environment layouts.

Layer responsibilities and applicable naming rules are mandatory; example trees show their intended organization, not a requirement to create every illustrated file. Create only needed directories. Existing structure changes follow the migration rule in [`../SKILL.md`](../SKILL.md); report unrelated debt instead of automatically migrating the whole project. Entries marked `optional` are prohibited unless actually needed.

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
- `mapper/` — persistence access when using MyBatis-Plus (MP) mappers.
- `entity/` — persistence models.
- `config/` — framework/infrastructure configuration.
- `exception/` — project/domain exceptions when they have clear ownership.

新增包使用上述单数名称 `service/`。既有 `services/` 的改名遵循入口的迁移选择；已明确授权局部迁移时按确认范围执行。

When several domains or substantial modules exist, subdivide the relevant layer by domain rather than accumulating unrelated files: for example `controller/order/`, `dto/request/order/`, `dto/response/order/`, `service/order/impl/`, `mapper/order/` and `entity/order/`. A cohesive single-domain module may keep a shallow layout. Existing domain-first layouts may place these responsibilities under `order/`; preserve that consistent ownership rather than adding a second layout. The business interface and implementation remain paired under their owner.

Create `mapper/` only when the project uses mapper-based persistence. A JPA or other persistence framework keeps its actual repository/access boundary instead of adding MP-shaped packages. No persistence layer is required for an application without persistence. DTOs, entities, enums and configuration remain distinct responsibilities; do not place them together just because a service uses them.

### Java type ownership

`service/` owns business contracts and orchestration implementations. It is not the default home for every type consumed or produced by a service. Classify a type from its fields, behavior, annotations, callers and method signatures; `record`, Lombok `@Data`, a `Context`/`Result`/`Model` suffix, or proximity to a caller does not establish ownership.

For an ordinary layer-first Spring project, use these owners. Reuse an explicitly established equivalent owner in a domain-first layout; do not introduce a parallel layout. Dedicated multi-module ownership is described below.

| Type responsibility | Owner | Boundary |
|---|---|---|
| HTTP input/output data | `dto/request/<domain>/`, `dto/response/<domain>/` | Keep transport contracts separate from persistence and service implementations. |
| Pure internal command, task context or service result passed between components | `dto/internal/<domain>/` | No HTTP exposure is required to be a DTO; do not disguise internal contracts as HTTP responses. Existing message contracts use the actual message owner, such as `dto/message/<domain>/`. |
| Non-persistent domain value, state or invariant | `domain/<domain>/model/` | A value object may own normalization, equality or invariant behavior without becoming a service or requiring an interface. Do not give it ORM annotations merely to fit `entity/`. |
| Database-mapped entity | `entity/<domain>/` | Requires actual persistence responsibility; fields alone do not make a type an entity. |
| Domain state enum or fixed domain constants | The existing domain-owned `enums/` or `constants/`; otherwise `domain/<domain>/enums/` or `domain/<domain>/constants/` | Do not accumulate these in `service/` or global `CommonConstants`. Tunable parameters still belong in configuration, never constants. |
| External provider payload, raw response or parser model | `integration/<provider>/model/` or the established integration contract owner | Business orchestration consumes the integration boundary; it must not become the owner of provider protocol types. |
| Framework configuration or bound settings | `config/` or the established infrastructure configuration owner | Do not place settings in a service model or a constants holder. |

The paths above are destinations for actual types, not a directory-generation template. Preserve explicit project conventions and migration scope from the entrypoint. An existing package name or an agent-generated type's current location is not itself a convention overriding these rules. In a dedicated `*.biz` project, put contract data in the DTO module and domain values/states in the domain module; do not create model containers in Biz merely because it calls them.

Nested-type exception:

- A `private` nested/local record or class may remain with one implementation when it is a temporary intermediate result, never appears in an exposed contract and has no independent domain or integration ownership. Do not create an extra file solely to eliminate such a local tuple.
- A public/protected nested record used by another component is a shared type, even if its only callers are services. Move it to its actual contract/domain/integration owner within authorized migration scope. Do not wrap a public model inside `*ServiceImpl`, a parser or a validator to evade placement rules.
- Access modifiers alone do not determine ownership: a private ORM entity, provider schema or independent domain value still belongs to its actual owner. Conversely, a meaningful domain value object does not gain an `interface + impl/` pair merely because it has methods.

For example, in a layer-first project, a field-only `TaskContext` passed from a worker to handlers belongs in `dto/internal/task/`; a metadata fingerprint with normalization and comparison invariants belongs in `domain/intelligence/model/`; an externally consumed raw model response belongs to the integration owner. A private `MatchCandidate` tuple used only inside one matching implementation may remain nested. Do not change existing names or public contracts merely to achieve these placements.

During review, enumerate the misplaced top-level/exposed nested types with evidence and intended ownership. Do not conclude that all field-bearing classes are entities, move every internal type to `dto/response/`, or regard a checker exit code as proof of correct placement.

### Multi-Maven / multi-module project with dedicated `*.biz`

When a multi-module Maven project separates business logic into modules such as `community.biz`, the `biz` module owns business contracts and implementations:

```text
middleware-arena-community/
├── community.biz/
│   ├── src/main/java/com/mware/community/biz/
│   │   ├── comment/
│   │   │   ├── impl/
│   │   │   │   ├── CommentCacheImpl.java
│   │   │   │   └── CommentServiceImpl.java
│   │   │   ├── CommentCache.java
│   │   │   └── CommentService.java
│   │   ├── config/
│   │   │   ├── CommunityScheduleConfig.java
│   │   │   ├── RabbitFavoriteConfig.java
│   │   │   ├── RabbitLikeConfig.java
│   │   │   └── RedisConfig.java
│   │   ├── consumer/
│   │   │   ├── impl/
│   │   │   │   ├── FavoritePersistenceConsumerImpl.java
│   │   │   │   ├── LikePersistenceConsumerImpl.java
│   │   │   │   └── LikeStatisticsConsumerImpl.java
│   │   │   ├── FavoritePersistenceConsumer.java
│   │   │   ├── LikePersistenceConsumer.java
│   │   │   └── LikeStatisticsConsumer.java
│   │   ├── favorite/
│   │   │   ├── impl/
│   │   │   │   ├── FavoriteRedisStoreImpl.java
│   │   │   │   ├── FavoriteServiceImpl.java
│   │   │   │   └── FavoriteStreamRelayImpl.java
│   │   │   ├── FavoriteRedisStore.java
│   │   │   ├── FavoriteService.java
│   │   │   └── FavoriteStreamRelay.java
│   │   ├── follow/
│   │   │   ├── impl/
│   │   │   │   └── FollowServiceImpl.java
│   │   │   └── FollowService.java
│   │   ├── like/
│   │   │   ├── impl/
│   │   │   │   ├── LikeRedisStoreImpl.java
│   │   │   │   ├── LikeServiceImpl.java
│   │   │   │   └── LikeStreamRelayImpl.java
│   │   │   ├── LikeRedisStore.java
│   │   │   ├── LikeService.java
│   │   │   └── LikeStreamRelay.java
│   │   ├── outbox/
│   │   │   ├── impl/
│   │   │   │   └── OutboxRelayImpl.java
│   │   │   └── OutboxRelay.java
│   │   ├── post/
│   │   │   ├── impl/
│   │   │   │   └── PostServiceImpl.java
│   │   │   └── PostService.java
│   │   └── search/
│   │       ├── impl/
│   │       │   └── SearchServiceImpl.java
│   │       └── SearchService.java
│   └── pom.xml
├── community.domain/
│   ├── src/main/java/com/mware/community/domain/
│   │   ├── Comment.java
│   │   ├── CommunityPost.java
│   │   ├── ConsumerEvent.java
│   │   ├── EventOutbox.java
│   │   ├── Follow.java
│   │   ├── PostFavorite.java
│   │   └── PostLike.java
│   └── pom.xml
├── community.dto/
│   ├── src/main/java/com/mware/community/dto/
│   │   ├── message/
│   │   │   ├── FavoriteEvent.java
│   │   │   └── LikeEvent.java
│   │   ├── request/
│   │   │   ├── CommentRequest.java
│   │   │   └── CreatePostRequest.java
│   │   └── response/
│   │       ├── CommentResponse.java
│   │       ├── FavoriteStatusResponse.java
│   │       ├── FollowStatusResponse.java
│   │       ├── LikeStatusResponse.java
│   │       └── PostResponse.java
│   └── pom.xml
├── community.mapper/
│   ├── src/main/java/com/mware/community/mapper/
│   │   ├── CommentMapper.java
│   │   ├── CommunityPostMapper.java
│   │   ├── ConsumerEventMapper.java
│   │   ├── EventOutboxMapper.java
│   │   ├── FollowMapper.java
│   │   ├── PostFavoriteMapper.java
│   │   └── PostLikeMapper.java
│   └── pom.xml
├── community.test/
│   ├── src/test/java/com/mware/community/test/
│   │   └── CommunityApiSmokeTest.java
│   └── pom.xml
├── community.web/
│   ├── .omc/state/
│   │   ├── sessions/a1e40752-a9cf-45d2-8898-6baf0fe31580/
│   │   │   └── pre-tool-advisory-throttle.json
│   │   └── idle-notif-cooldown.json
│   ├── logs/
│   │   ├── .gitignore
│   │   ├── .gitkeep
│   │   └── community-service.log
│   ├── src/main/
│   │   ├── java/com/mware/community/
│   │   │   ├── config/
│   │   │   │   └── MybatisPlusConfig.java
│   │   │   ├── controller/
│   │   │   │   └── CommunityController.java
│   │   │   └── CommunityApplication.java
│   │   └── resources/
│   │       ├── .omc/state/sessions/0be9f647-aeda-4ea6-998f-45f95c4b391f/
│   │       │   └── pre-tool-advisory-throttle.json
│   │       ├── application-sharding.yml
│   │       └── application.yml
│   └── pom.xml
├── sql/
│   ├── init.sql
│   ├── init_like_shards.sql
│   ├── upgrade_favorite_state.sql
│   ├── upgrade_like_final.sql
│   └── upgrade_like_shards_to_state.sql
├── .gitignore
├── Dockerfile
├── README.md
└── pom.xml
```


以上示例按社区服务的实际源码展开，覆盖 Maven 聚合配置、业务模块、启动入口、资源、测试和 SQL 脚本；其中业务接口与实现仍归属各自领域。

| 模块 | 职责 | 依赖边界 |
|---|---|---|
| `community.dto` | 请求、响应和消息契约 | 不依赖业务实现、Mapper 或 Web |
| `community.domain` | 持久化实体与领域定义 | 不依赖 Web 或业务实现 |
| `community.mapper` | MyBatis-Plus（MP）数据访问；复杂 SQL 确有需要时放在 `src/main/resources/mapper/` | 使用 `domain`，不调用业务层 |
| `community.biz` | 业务接口与实现、Redis 状态、消息消费及事件投递 | 使用 DTO、领域定义和 Mapper，不依赖 Web |
| `community.web` | Spring Boot 启动、Controller、Web 配置和应用配置 | 调用业务接口，使用 DTO；Controller 不直接调用 Mapper |
| `community.test` | 跨模块 API 冒烟或集成测试 | 测试代码放在 `src/test/`；仅测试依赖应用模块 |
| `community.feign`（按需） | 对外提供社区服务的 Feign 调用契约 | 使用 DTO，不依赖 Web、Biz 或 Mapper |

截图中的 `advert.fegin` 若承担 Feign 契约职责，新建对应模块使用 `community.feign`；保留既有模块名，不自动重命名。当前社区服务没有该模块，不为凑齐截图创建空模块。需要时添加 `community.feign/pom.xml` 和 `src/main/java/com/mware/community/feign/CommunityClient.java`，并注册到父 POM。

各子模块保留自己的 `pom.xml`；根 `pom.xml` 使用 `packaging=pom` 聚合实际模块。`web` 负责应用打包，DTO、Domain、Mapper 和 Biz 作为库模块。独立测试模块不替代各模块按需编写的单元测试。配置文件、Mapper XML、Lua 脚本仅在确有需要时放入所属模块的 `src/main/resources/`，不预建空目录。

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

既有模块迁移须遵循入口的迁移选择；不得把基础设施或领域实现仅通过改名变成 API 契约。

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

Do **not** create `utils/`, `common/`, `base/`, or a generic `core/langgraph/` just because they appear in another template. Add them only when the project has a concrete need. 既有包的调整遵循入口的迁移选择，不扩大已确认范围。

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

事务由公开业务入口统一管理，repository 不独立提交同一业务操作。普通查询通常无需事务包装；避免在事务中等待慢速外部调用。

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

小页面可直接组织在页面文件及相邻模块中；功能变复杂时再聚合到 `features/<功能>/`。功能内部不得直接依赖其他功能的私有组件；共享内容须有明确契约。不要同时在全局与功能目录中维护两套请求、状态或类型。既有结构迁移遵循入口的迁移选择；已有会话授权时不重复询问。

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
