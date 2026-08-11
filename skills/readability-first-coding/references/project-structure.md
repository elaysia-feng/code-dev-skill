# Project Structure

Directory structure separates responsibilities. It does **not** require common parent classes, interfaces, converters, or utility modules.

## Java Backend

```
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

### controller

Receives parameters, calls Service, returns results.

### dto/request

Request body data for incoming API calls.

### dto/response

Response body data returned to clients.

### service

Business logic goes here directly. Do **not** create `Service` interface + `ServiceImpl` by default. Only split when:

- Multiple implementations actually exist
- The existing project convention requires it
- The user explicitly requests it

### mapper

Database access layer.

### entity

Database table mappings.

## Python Backend (FastAPI + LangGraph)

Based on the popular FastAPI + LangGraph templates (`JoshuaC215/agent-service-toolkit`, `wassim249/fastapi-langgraph-agent-production-ready-template`, `fastapi/full-stack-fastapi-template`).

```
src/
├── main.py                       # FastAPI app entry point
├── api/
│   └── v1/                       # Route handlers (APIRouter), grouped by version
├── core/
│   ├── config.py                 # pydantic-settings, reads from env / .env
│   ├── llm.py                    # LLM client wrappers (ChatOpenAI, etc.)
│   ├── middleware.py
│   └── langgraph/                # LangGraph infrastructure (shared across graphs)
│       ├── state.py              # State / TypedDict definitions
│       ├── nodes.py              # Reusable node functions
│       ├── tools.py              # @tool decorated functions
│       └── graph.py              # Graph composition helpers
├── graphs/                       # LangGraph agent implementations
│   ├── __init__.py               # Registry mapping graph_id -> compiled graph
│   └── {agent_name}.py           # One compiled StateGraph per file
├── schemas/                      # Pydantic request/response models
├── services/                     # Non-agent business logic
├── models/                       # ORM models (SQLModel / SQLAlchemy)
├── memory/                       # Long-term memory (mem0, pgvector, etc.)
└── utils/
```

Optional at repo root (not under `src/`):

```
alembic/                          # Database migrations
tests/
pyproject.toml
.langgraph.json                   # LangGraph Studio / CLI graph declarations
```

### main.py

Application entry. Creates the `FastAPI` instance, registers routers from `api/v1/`, attaches middleware, and starts `uvicorn`.

### api/v1/

Route handlers using `APIRouter`. Each file corresponds to one resource or domain. Endpoints delegate to either a graph (from `graphs/`) or a service (from `services/`).

### core/config.py

`pydantic-settings` `BaseSettings` subclass. Centralized env-driven configuration. No business logic.

### core/llm.py

LLM client wrappers. One factory per provider (OpenAI, Anthropic, etc.). Returns `BaseChatModel` instances. Keep prompt templates in `core/prompts/` if they grow large.

### core/langgraph/

Shared LangGraph infrastructure used by multiple graphs:
- `state.py` — `TypedDict` or `BaseModel` defining the state shape consumed by nodes.
- `nodes.py` — Reusable node functions (LLM call, tool execution, routing).
- `tools.py` — `@tool` decorated functions exposed to the agent.
- `graph.py` — Graph composition helpers (e.g., building tool-calling loops).

### graphs/

**One compiled `StateGraph` per file.** Each file is self-contained: imports its state, nodes, and tools from `core/langgraph/`, builds the graph, and exports the compiled result.

Naming convention follows LangGraph official terminology (`graphs/` matches `langgraph.json`'s `graphs` key).

Registered centrally in `graphs/__init__.py` so the API layer can dispatch by graph name.

### schemas/

Pydantic models for request and response data. Each model owns its own validation (field validators or a `validate()` method). No global `BaseSchema`.

### services/

Business logic that is **not** an agent. Database operations, third-party API calls, orchestration outside of a graph. May call into `models/` for ORM access. **No separate `repositories/` layer** — services talk to `models/` directly via the SQLModel/SQLAlchemy session.

### models/

ORM models (`SQLModel`, `SQLAlchemy`). One file per table or aggregate.

### memory/

Long-term memory implementations (`mem0`, `pgvector`). Only present if the project uses long-term memory across sessions.

Same principles as Java — the directory structure organizes code by its role in the application (routes, config, schemas, graphs, services), not by abstract design-layer patterns (interface/impl, domain/infrastructure, strategy/factory).
