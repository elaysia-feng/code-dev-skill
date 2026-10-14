# API versioning and migration

These rules apply to HTTP APIs across languages. Preserve the project's existing versioning mechanism; do not add URL versions or version directories without a compatibility requirement.

## When to introduce a version

- Evaluate the public contract, including request/response shapes, validation, status codes, error semantics, authentication and observable business behavior. Breaking changes require an agreed compatibility strategy, not simply a renamed directory.
- Bug fixes, performance improvements, new endpoints and compatible optional fields ordinarily stay in the current version. Confirm actual client expectations: even additive response fields can break strict consumers.
- For a jointly controlled frontend and backend with no old-client compatibility requirement, an agreed coordinated update may modify the existing interface. Do not introduce v2 automatically for every change.

## Coexistence and code ownership

- When old clients must keep working, retain v1 routes and add v2 routes for changed contracts. Do not rename `v1/` to `v2/` and claim compatibility. Version only the endpoints that need different contracts; do not clone the entire API.
- Python package names do not determine public URLs. Inspect router prefixes and registration; use equivalent routing mechanisms in other frameworks. Do not accidentally mount unchanged endpoints under a new version prefix.
- Keep version-specific transport parsing, DTOs, response formatting and necessary adapters at API boundaries. For example, `api/v1/order/` and `api/v2/order/` can call the same `services/order/` business entry point. Place incompatible DTOs under distinct version owners, such as `schemas/order/v1/` and `schemas/order/v2/`; share types only while their contracts are actually identical.
- Do not copy `services/`, persistence models or database tables merely because an API version changes. If business behavior also changes, make the difference explicit in the owning business contract rather than hiding it in transport adapters or silently changing v1 behavior.

## Deployment and retirement

- Source changes take effect only after building and deploying the application. Ordinarily one application deployment serves both versions; v2 does not imply a separate service, port or deployment. Follow the existing architecture if independent deployment is actually required.
- Update and deploy affected clients when URLs or contracts change. While old and new application instances may coexist during rollout, database and configuration changes must remain compatible with the supported versions; do not destructively rename/drop fields as a side effect of adding v2.
- Document the supported versions, client migration steps and retirement conditions. Removing v1 requires an agreed compatibility decision and evidence that the supported old clients have migrated; do not remove it solely because v2 was deployed.
- Implementing API changes does not authorize publishing, deploying to production or retiring live interfaces. Carry out those actions only within the user's authorization.

## Validation

Test the affected versions' externally visible routes, request validation, response shapes and errors. Include regression coverage for v1 when coexistence is required and verify both versions reach the intended business logic. Check router registration and API documentation for duplicate or accidentally changed routes. Report separately what was implemented, tested and deployed; directory renaming or successful imports alone do not establish compatibility.
