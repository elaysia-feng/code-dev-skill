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
> Easy to understand
> Directness
> Easy to modify
> Fewer unnecessary dependencies
> Less duplication
> Reusability
> Architectural elegance
```

Correctness is mandatory. Existing project conventions take precedence over this skill's defaults when they are consistent and relevant to the code being changed.

## Default behavior

1. Read the existing package/module structure before changing code.
2. Make the smallest coherent change that completes the requested behavior.
3. Keep business decisions close to where they are used.
4. Do not introduce a new layer, base class, interface, shared package, factory, strategy, wrapper, or helper solely to reduce line count.
5. Preserve existing architectural boundaries. Do not flatten an established repository/service/interface pattern just because this skill would not create it in a greenfield project.
6. Do not modify unrelated code or reorganize unrelated packages.
7. Prefer explicit control flow and clear names over clever syntax.

## Abstraction gate

Before creating or extracting an abstraction, require a concrete reason beyond "these lines look similar".

Good reasons include:

- The user explicitly asks for extraction or reuse.
- The project already has an established abstraction and the new code clearly belongs in it.
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
- **Necessary complexity**: transactions, security boundaries, domain state, integration boundaries, concurrency, or multiple implementations that justify additional structure.
- **Abstraction smell**: indirection that adds files/call hops without owning meaningful behavior.

When the user asks to refactor, refactor toward the stated goal. Do not use "readability first" as a reason to reject a requested extraction or redesign.

## LangGraph rule of thumb

- Small graph: graph-specific state/nodes/tools may stay together when the complete flow remains easy to read.
- Complex graph: split meaningful nodes into separate files under that graph's package.
- Put state/nodes/tools in shared `core/langgraph/` only when they are genuinely shared by multiple graphs.
- `__init__.py` may remain empty or provide lightweight exports. Do not put business logic or side effects in it.

See `references/python-guidelines.md` and `references/project-structure.md` for the detailed layout.

## Automated checker

`scripts/check-abstraction-smell.py` is a best-effort heuristic, not an architectural authority. Treat its findings as review prompts, not automatic failures. Existing conventions and explicit user requirements may legitimately trigger warnings.

Run when useful:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check-abstraction-smell.py . --lang auto
```

## Final check

Before finishing:

- Does the change follow the surrounding project structure?
- Is each new file/package/layer necessary for a concrete reason?
- Can the main flow be understood without unnecessary cross-file jumps?
- Did the change introduce a generic dumping-ground module?
- Did it modify unrelated code?
- Did it preserve correctness, tests, and required framework behavior?
