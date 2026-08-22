---
name: readability-first-coding
description: >-
  Coding conventions for real Java backend, Java microservice, and Python backend
  (FastAPI + LangGraph) implementation, modification, review, and refactoring work.
  Preserve existing project conventions, prefer direct readable code, avoid speculative
  layers and abstractions, and extract shared code only when there is a concrete reason
  beyond reducing duplicated lines.
license: MIT
compatibility: >-
  Intended for Java/Spring backend, Java microservice, Python backend, FastAPI, and
  LangGraph application projects. Detailed rules are provided in references/.
---

# Readability First Coding

## Priority

For correct solutions, prefer:

```text
Existing project consistency
> Explicit project constraints
> Easy to understand
> Directness
> Easy to modify
> Fewer unnecessary dependencies
> Less duplication
> Reusability
> Architectural elegance
```

Correctness is mandatory. Existing project conventions take precedence over this skill's defaults when they are consistent and relevant to the code being changed.

## Mandatory Java business-contract rule

Java business code uses interface-first design. The package shape depends on the project type.

### Multi-Maven / multi-module project

When a multi-module Maven project has a dedicated `*.biz` module, business-behavior components inside that module must expose interfaces and place concrete implementations under `impl/`:

```text
community.biz/
└── src/main/java/com/mware/community/biz/
    ├── favorite/
    │   ├── FavoriteService.java
    │   ├── FavoriteRedisStore.java
    │   ├── FavoriteStreamRelay.java
    │   └── impl/
    │       ├── FavoriteServiceImpl.java
    │       ├── FavoriteRedisStoreImpl.java
    │       └── FavoriteStreamRelayImpl.java
    └── like/
        ├── LikeService.java
        ├── LikeRedisStore.java
        ├── LikeStreamRelay.java
        └── impl/
            ├── LikeServiceImpl.java
            ├── LikeRedisStoreImpl.java
            └── LikeStreamRelayImpl.java
```

### Ordinary monolithic Spring project

When there is no dedicated Maven `*.biz` module, put business services under the project's `service/` or `services/` package and still use interface + `impl/`:

```text
com.example.order/
├── controller/
├── service/
│   ├── OrderService.java
│   ├── PaymentService.java
│   └── impl/
│       ├── OrderServiceImpl.java
│       └── PaymentServiceImpl.java
├── mapper/
└── entity/
```

Use the repository's existing `service` vs `services` naming; do not rename a coherent project only for this skill.

### Interface-first rules

- `<Name>.java` is the public business contract.
- `impl/<Name>Impl.java` is the concrete implementation.
- Spring stereotypes such as `@Service` / `@Component` belong on the implementation.
- Callers inject and depend on the interface type, never `*Impl` directly.
- In a dedicated `*.biz` module, apply the rule to business-behavior collaborators such as Service, Store, Relay, Manager, Handler, Processor, and gateway/client adapters.
- In an ordinary monolith, the required interface-first boundary applies to business services under `service/` / `services/`; do not create interfaces for unrelated DTO/entity/config/helper types merely for symmetry.
- DTO/entity/value objects, enums, exceptions, annotations, configuration classes, and constants are not interface candidates.

The purpose is a stable business contract for extension/replacement, testing, interception/AOP, and observability boundaries. The interface itself does not create observability; it gives the project a consistent contract boundary where those concerns can be attached.

## Default behavior

1. Read the existing package/module structure before changing code.
2. Identify whether the Java project is multi-module with a dedicated `*.biz` module or an ordinary monolith before creating business classes.
3. Make the smallest coherent change that completes the requested behavior.
4. Keep business decisions close to where they are used.
5. Do not introduce a new layer, base class, shared package, factory, strategy, wrapper, or helper solely to reduce line count, except where the mandatory Java interface-first business rule requires the contract/implementation pair.
6. Preserve existing architectural boundaries. Do not flatten an established repository/service/interface pattern.
7. Do not modify unrelated code or reorganize unrelated packages.
8. Prefer explicit control flow and clear names over clever syntax.

## Abstraction gate

Before creating or extracting an abstraction, require a concrete reason beyond "these lines look similar".

Good reasons include:

- The user explicitly asks for extraction or reuse.
- The project already has an established abstraction and the new code clearly belongs in it.
- The Java business layer is governed by the mandatory interface-first rule above.
- Multiple implementations genuinely need one contract.
- Several callers share the same stable technical concern or invariant and keeping separate copies would create a real consistency risk.
- A framework/API boundary requires the abstraction.

If none applies, keep the logic local even when some code repeats.

Do not create generic `common`, `util`, `utils`, `shared`, `base`, `framework`, `helpers`, `support`, or `infrastructure` packages as dumping grounds. If an existing project already uses one of these packages, place code there only when its ownership is clear and consistent with neighboring code.

## Reference routing

Load only the references relevant to the task before implementing structural changes:

| Context | Read |
|---|---|
| Java backend / Spring Boot | `references/java-guidelines.md` |
| Python backend / FastAPI / LangGraph | `references/python-guidelines.md` |
| Java microservices | `references/microservice-guidelines.md` plus `references/java-guidelines.md` |
| Creating or changing directories/modules | `references/project-structure.md` |
| Unsure about preferred shape | `references/examples.md` |

Do not load every reference file by default.

## Review and refactor behavior

When reviewing existing code, distinguish between:

- **Existing convention**: consistent architecture already used by the project. Preserve it unless the user asks to change it.
- **Explicit project constraint**: Java business services/components use interface-first contracts; the physical location differs between multi-module `*.biz` projects and monolith `service/` projects.
- **Necessary complexity**: transactions, security boundaries, domain state, integration boundaries, concurrency, or multiple implementations that justify additional structure.
- **Abstraction smell**: indirection that adds files/call hops without owning meaningful behavior and is not required by an explicit project rule.

When the user asks to refactor, refactor toward the stated goal. Do not use "readability first" as a reason to reject a requested extraction or redesign.

## LangGraph rule of thumb

- Small graph: graph-specific state/nodes/tools may stay together when the complete flow remains easy to read.
- Complex graph: split meaningful nodes into separate files under that graph's package.
- Put state/nodes/tools in shared `core/langgraph/` only when they are genuinely shared by multiple graphs.
- `__init__.py` may remain empty or provide lightweight exports. Do not put business logic or side effects in it.

See `references/python-guidelines.md` and `references/project-structure.md` for the detailed layout.

## Automated checker

`scripts/check-abstraction-smell.py` is a best-effort heuristic, not an architectural authority. Treat its findings as review prompts, not automatic failures. Existing conventions and mandatory Java business interface contracts may legitimately trigger warnings.

Run when useful:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check-abstraction-smell.py . --lang auto
```

## Final check

Before finishing:

- Does the change follow the surrounding project structure?
- For Java, did you identify multi-module `*.biz` vs ordinary monolith first?
- In a multi-module `*.biz` project, are business components interfaces with implementations under the local `impl/` package?
- In a monolithic project, are business services under `service/` / `services/` and implemented through `impl/` classes?
- Do callers depend on interfaces rather than `*Impl`?
- Is each additional abstraction beyond the required business contract justified?
- Can the main flow be understood without unnecessary cross-file jumps?
- Did the change introduce a generic dumping-ground module?
- Did it modify unrelated code?
- Did it preserve correctness, tests, and required framework behavior?
