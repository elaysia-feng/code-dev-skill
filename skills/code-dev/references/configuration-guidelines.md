# Configuration and hardcoding prevention

These mandatory rules apply to implementation, refactoring and review in Java, Python, TypeScript/JavaScript, C++ and C#.

## Configuration files and environment isolation

- Separate shared defaults from development, test and production differences. Defaults must not implicitly select development databases, test accounts or other environment-specific settings. Use the project's framework-native file formats, environment names and loading mechanisms; do not force `.env` on every non-Java project.

| Language / framework | Configuration mechanism |
|---|---|
| TS/JS, Node.js, Python | Projects supporting dotenv may use `.env` for shared defaults and `.env.development`, `.env.test`, `.env.production` for differences; follow an existing framework mechanism when present |
| Java / Spring Boot | `application.yml` and `application-dev.yml`, `application-test.yml`, `application-prod.yml`, selected through Spring profiles |
| Plain Java / other Java frameworks | Project configuration files and native environment selection; do not introduce Spring just for configuration formats |
| C# / ASP.NET Core | `appsettings.json` and `appsettings.Development.json`, `appsettings.Test.json`, `appsettings.Production.json`; select the test environment explicitly rather than assuming automatic activation |
| Other C#/.NET projects | Existing configuration providers; otherwise use simple configuration files and a single loading entry point |
| C++ | The project's JSON, TOML, INI or equivalent format, separating shared values and environment differences; use explicit environment selection and loading order without adding a heavyweight configuration framework |

- Select the runtime environment explicitly. Do not permanently enable development in source code or shared configuration. Tests use independent databases, cache namespaces, messaging resources or isolated substitutes, not development or production resources.
- Use native framework loading. For custom `.env` or other loaders, load shared configuration before the selected environment file; environment-specific values override shared defaults, and injected environment variables take precedence over files. Creating files without wiring up loading is insufficient. For frameworks, document and verify actual precedence, including command-line overrides.
- Application code reads through one configuration entry point; business modules must not parse files independently. Frontends expose public configuration only; database passwords, private keys and server tokens must never enter browser bundles.
- Put non-sensitive defaults in configuration files. Do not maintain a second set of fallbacks in business code, environment-variable reads or annotations. Missing required settings must fail startup with the key name, without disclosing secret values. Production must not silently fall back to development configuration.
- Inject real passwords, tokens and private keys through runtime environment variables or a secret service. Spring Boot YAML may bind `${VARIABLE_NAME}` placeholders; other formats use overrides supported by their loaders. Do not assume JSON or INI expands placeholders automatically. Ignore files containing real secrets and local overrides in version control; provide secret-free examples and environment templates documenting keys, purposes and environment selection.

## No hardcoded configuration or business magic values

- Addresses, ports, database connections, file paths, service endpoints, timeouts, retry counts, switches, rate limits and tunable business parameters belong in configuration and must be read through the configuration entry point.
- Do not embed environment-specific values or secrets in source code, annotation arguments, scripts or build files. Moving them to `static final` or a constants module does not externalize configuration.
- Represent fixed business states and repeated values with meaningful domain constants or enums, including error codes, permission identifiers and protocol values. Avoid scattered business magic values. Do not extract every number or string mechanically: interpret loop initializers such as `0`, empty strings, declarative framework metadata such as routes and configuration keys, test assertions and isolated fixtures according to their meaning. None may contain real secrets or addresses dependent on real environments.
- Review default arguments in configuration reads, annotation defaults and exception fallbacks for bypasses. Determine hardcoding by meaning; searching for numbers or strings alone does not prove compliance.

## Validation

Use secret-free temporary configuration to verify loading, override precedence and missing required settings across all three environments. Verify Spring Boot profiles, ASP.NET Core environment names and configuration providers, or the actual startup loader for other projects. Check that production does not accidentally select development resources and that frontend artifacts and committed contents contain no secrets. Report validation methods and unverified items.
