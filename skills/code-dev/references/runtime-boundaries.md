# Runtime responsibility boundaries

Read the relevant parts when changing persistence, external integrations or background execution. These rules apply across languages; use existing framework mechanisms rather than inventing generic wrappers.

## Persistence and transactions

- Own the transaction at the business entry point that needs atomicity, not independently inside each persistence helper. Helpers must not commit early when their caller owns a larger transaction. Ordinary reads need no transaction unless a consistency requirement calls for one.
- Validate state transitions at the write boundary. A read followed by an unconditional update may race; use the project's conditional update, version check or locking strategy when concurrent writes matter, and inspect affected-row counts. Do not claim atomicity from an annotation or a status check alone.
- Use the project's migration mechanism for database schema changes. Do not silently drop/recreate data, edit already-applied shared migrations or substitute startup table creation for a required migration. Check compatibility with supported application versions and report migration validation separately from import/build checks.

## External I/O, errors and retries

- Configure bounded timeouts for external calls. Use cancellation and resource cleanup supported by the runtime; do not leave detached tasks or clients unmanaged.
- Retry only identified transient failures, with bounded attempts and suitable backoff. Ensure side-effecting operations are idempotent or have an explicit deduplication/compensation mechanism before retrying; avoid multiplying retries across several layers.
- Keep business rejection, invalid input and infrastructure failure distinct. Translate errors at the relevant API/integration boundary; do not swallow failures, fabricate successful results or expose raw internal exceptions to clients.
- Log useful operation/context identifiers while redacting credentials, tokens and sensitive payload fields. Avoid duplicate logging at every layer and do not introduce a new logging stack for an ordinary change.

## Background work and schedulers

- Register/start background work through the application's lifecycle, not as an import or static-initialization side effect. Shut down gracefully and release owned resources.
- Check what happens with multiple workers/replicas and overlapping executions. An in-process scheduler may run once per process, not once per deployment; when duplicate execution matters, use the project's coordination mechanism or idempotent processing and verify the behavior.
- Define retry and failure handling for jobs and messages. Acknowledge work according to the actual processing guarantee; do not claim exactly-once behavior without evidence.

## Verification

For Java/Spring, run the skill's `scripts/check-java-boundaries.py <project-root> --fail-on warning`. It flags direct transaction self-invocation and integration interfaces with no detected production type consumer, including same-domain services using HTTP directly. Confirm actual proxy/wiring paths: reflective registration, generated consumers, overloads and indirect call chains require manual inspection. Static results do not establish atomicity, integration coverage or runtime behavior.

Use relevant behavior checks for the changed boundary: rollback and conflicting writes, timeout/failure paths, repeated delivery or overlapping jobs as applicable. Use isolated resources, and distinguish code/build/import evidence from actual persistence or runtime execution. Do not add unrelated infrastructure merely to satisfy a checklist.
