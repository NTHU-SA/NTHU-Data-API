# Copilot Instructions

## Development Setup

Use Python 3.14+ and uv. Run commands from the repository root. Dependencies
and tool configuration are declared in `pyproject.toml` and locked in `uv.lock`.

### Installing Dependencies

```sh
# Install runtime, development, and test dependencies from the lockfile
uv sync --all-groups
```

### Pre-commit Setup

This project uses pre-commit hooks to ensure code quality. Before making commits:

```sh
# Install pre-commit hooks
uv run pre-commit install

# Run pre-commit on all files manually
uv run pre-commit run --all-files
```

## Running Tests

Run the smallest relevant set of tests while iterating, then the full suite
for changes affecting shared services, lifecycle, or public contracts.

```sh
# Run tests
uv run --group test pytest tests

# Run tests in parallel
uv run --group test pytest -n auto tests

# Run tests with coverage
uv run --group test pytest tests --cov=src --cov=tests --cov-report=term-missing

# Match the CI coverage reports and 85% threshold
uv run --group test pytest -n auto tests --cov=src --cov=tests --cov-report=xml --cov-report=html:coverage --cov-fail-under=85
```

Tests use mock transports and injected clocks; the default suite blocks real
HTTPX network traffic. Preserve that isolation when adding tests. Dataset lifecycle
coverage is in `tests/test_data_manager.py` and `tests/test_runtime_lifecycle.py`.
Use the matching endpoint, service, MCP, or middleware tests for behavior changes.

## Code Style

This project uses:
- **black** for code formatting
- **isort** for import sorting

Both are configured in `pyproject.toml` with a line length of 100 and enforced
by pre-commit hooks. Black targets Python 3.14; isort uses the Black profile.

## Project Structure

| Path | Responsibility |
| --- | --- |
| `main.py` | Root launcher; delegates to `data_api.api.main` |
| `src/data_api/api/` | FastAPI app, middleware, REST routers and response schemas |
| `src/data_api/mcp/` | MCP server, tools and tool errors |
| `src/data_api/domain/` | Domain models, adapters and shared services |
| `src/data_api/models/` | Transport-neutral dataset, value and validation models |
| `src/data_api/runtime.py` | App-owned services, live clients and request-local runtime binding |
| `src/data_api/data/` | Dataset manager, snapshot cache and validation |
| `src/data_api/core/` | Settings, dataset configuration, constants and shared exceptions |
| `src/data_api/utils/` | Shared calendar, search and schema helpers |
| `tests/` | Endpoint, domain, MCP and lifecycle tests |

Keep business logic in shared domain services so REST and MCP stay consistent.
Data and domain code must not import REST schemas; use `data_api.models` for shared
models. REST schema modules retain import facades and HTTP-specific parameters.
`create_app()` creates an independent runtime and MCP transport. The exported app
uses the default runtime, also used by standalone MCP calls. Bind services through
`get_runtime()` at transport boundaries; inject dataset managers into domain
services. Never change the active runtime by mutating a process-global variable.
Within each app, REST and MCP share snapshots; separate app instances must not
share locks, clients or service state. Prepared bus snapshots contain
`PreparedBusData`, not live service instances.

Live electricity and library clients are separate from the dataset client and
are owned by the app lifespan, including cleanup on startup failure. Standalone
service calls own temporary clients; the three electricity requests share one
client. Do not add live snapshot fallback or automatic retries. Internal MCP
result types do not change public tool output annotations or schemas.
Start the application with `uv run python main.py`; `.env.template` provides
local configuration. Settings load environment variables and `.env`.

## Public Contracts and Compatibility

Read [the API guide](../docs/api-guide.md) before changing query semantics,
response shapes, route aliases, or MCP tools. It records supported endpoints
and migration differences that are not obvious from OpenAPI alone.

- MCP tools explicitly declare stable English `name` values and Traditional
  Chinese display `title` values. Internal Python renames must not change public
  names. Preserve argument defaults, limits, validation and response shapes.
- Only register supported slashless routes; keep FastAPI's ordinary slash redirects.
  The deprecated operations were removed in 3.0.0. Do not restore compatibility
  aliases or change existing operation IDs for internal renames.
- Maintain one live API version, without versioned URL prefixes. Minor/patch
  releases preserve contracts; announce deprecations and replacements before a
  major removal. Update and review REST/MCP baselines together with migration notes.
- `pyproject.toml` is the version source; use installed distribution metadata in
  Python and keep the local project's `uv.lock` version synchronized. Release
  builds validate an exact stable `vX.Y.Z` tag and must not rewrite source versions.
  `cloudbuild.yaml` validates, builds, publishes and updates the existing Cloud Run
  service; trigger filters are managed in GCP. Do not reintroduce custom deployment
  orchestration or GCS locks. See [releasing](../docs/releasing.md).
- Preserve REST/MCP search differences: MCP course search uses case-sensitive
  literal substrings; REST course GET text filters use regex; the POST DSL defaults to exact
  matching. Invalid regex must return 422 even with an empty dataset.
- Courses use the publisher's normalized 33-field model, not the old string fields.
  GET numeric/boolean filters and POST matchers use native types. Array leaf paths
  use independent ANY predicates; missing union keys are not explicit null.
  Preserve unknown values and `parsing_issues`, without guessing source repairs.
  Latest uses `courses/latest.json`; discover semesters from `courses/sources.json`
  and load `courses/semesters/{semester}.json` on demand. Hold snapshots and their
  versions locally per request, never switch shared active-semester state.
  Invalid, unpublished and unavailable semesters are 422, 404 and 503 respectively;
  stale/unverified catalog absence cannot establish 404. Never fall back to latest.
  MCP keeps its teacher convenience filter but returns full normalized courses.
- Apply all search filters before result limits. Never mutate cached datasets
  while filtering, including nested directory people and newsletter articles.
- Nullable publisher metadata defaults to `null`, but supplied values must still
  validate. Required identifiers, non-nullable titles, event boundaries and
  dataset structure must remain required.
- Dining opening-day checks are schedule-note heuristics, not live availability.
  `today` uses Asia/Taipei; do not silently change dining or bus semantics.
- Calendar IDs reserve `library-` for library sources; reject duplicate source
  IDs. Combined lists require both usable snapshots, while individual calendar
  and event requests only load their own source. Preserve overlap filtering,
  exclusive all-day ends, ordering, pagination and source-version headers.
- The exported app serves both REST and MCP. Preserve CORS and `X-Process-Time`
  even for unexpected failures before a response starts, including dependency
  and response validation errors. Expose `X-Total-Count`, `X-Data-Commit-Hash`,
  and `X-Process-Time` to browser clients from configured origins.
- `GET /` is lightweight discovery, not readiness: it must not read datasets or
  make upstream requests, and its name/version must match FastAPI metadata.
  It remains hidden from OpenAPI.

### Error Handling

With no usable dataset snapshot, return REST 503 or a controlled MCP tool error,
not a successful empty result. Valid empty datasets must still succeed.
An unknown version omits `X-Data-Commit-Hash`; never invent a version.

Live electricity, library space, and lost-and-found integrations use separate
on-demand HTTP clients, not dataset snapshots or last-known-good guarantees.
Preserve REST 502 for upstream connection/HTTP failures or invalid JSON/HTML/data,
504 for upstream timeouts, and 500 for unexpected internal errors.
Use fixed, safe `detail` messages and keep upstream URLs and exception details
in server logs, not public responses. Document these responses in OpenAPI.
MCP live failures must be tool errors (`isError: true`), not successful
`{"error": ...}` results; valid empty results still succeed.

Lost-item pages must contain exactly the expected table columns (any order,
without duplicates) or the library's explicit empty-result message on its
lost-and-found page. Unexpected columns, missing tables and malformed rows
are upstream errors.

## Dataset Lifecycle

Published datasets at `NTHU_DATA_URL` are the persistent source of truth.
Each process owns disposable in-memory snapshots, per-dataset async locks,
freshness/error metadata and one lifespan-managed HTTPX client. REST and MCP
share these services, including transformed courses and bus indexes. Multiple
workers and Cloud Run instances do not share state.

Refresh is request-driven: there is no permanent background loop, disk cache,
distributed lock or cross-instance synchronization. Startup prefetches published
REST/MCP datasets, including maps, library RSS and library calendars.
The unpublished root `libraries.json` is not required. Prefetch failure must
not prevent the application or unrelated datasets from starting.

- `FILE_DETAILS_CACHE_EXPIRY` is positive seconds (default 300). Within the TTL,
  use the active snapshot without upstream access. The shared manifest's reuse
  must not extend its freshness. After expiry, one caller per dataset checks the
  version while concurrent callers wait and re-check. Unrelated downloads must
  not block each other.
- A known matching version avoids downloading. A changed or previously unknown
  active version requires download, optional checksum verification, validation
  and complete transformation before atomic installation. Valid `[]` or `{}`
  replaces older records when the dataset schema accepts that shape.
- Manifest failure or an unknown expected version retains existing data as
  **unverified**. With no snapshot, attempt direct loading and keep it unverified.
  Unknown versions are never a confirmed match.
- Failed downloads, invalid schemas or failed transformations preserve the
  last-known-good snapshot as **stale**. Bound attempts to one per TTL, including
  failed cold starts; cancellation must not prevent later retries. Do not add
  automatic HTTP retries.
- `DATA_HTTP_TIMEOUT` is positive seconds (default 15) and controls the pooled
  client's connect/read/write/pool timeouts. Close the client on shutdown,
  including startup failure.

Last-known-good is instance-local availability, not durable storage. Restart or
scale-to-zero loses snapshots. A new instance can return 503 when upstream data
is unavailable, and instances can temporarily serve different versions.
Public per-object freshness/provenance metadata and product changes to dining
or bus semantics are outside this lifecycle contract.

### Published Manifest Contract

Consume `file_details.json` in the publisher's existing shape:

```json
{
  "file_details": {
    "courses": [
      {
        "name": "latest.json",
        "version": "opaque-version",
        "last_updated": "2026-09-27T22:24:37+08:00"
      }
    ],
    "libraries": [
      {"name": "rss.json", "version": "opaque-version"}
    ]
  }
}
```

Section plus `name` identifies the dataset path. Use only `version` as the version
identifier; ignore `last_commit` and do not use it as a fallback. Missing or null
`version` means unknown freshness. Versions are opaque equality tokens, not sortable revisions.
Verify the optional lowercase `sha256` digest of file bytes before installation
to prevent manifest/data publication races. Legacy manifests without checksums
remain supported but do not provide this integrity guarantee.

`last_updated` is optional publisher metadata, not a local load/check time.
Ignore extra fields; missing entries/versions mean unverified freshness.
Malformed entries, duplicate paths and malformed manifests must fail the check
safely. Do not reuse previous entries as evidence of a successful new check.
No publisher pipeline change is required.

### Diagnostics and Readiness

`app.state.datasets.states` exposes `snapshot`, `usable`, `freshness`,
`last_checked_at`, `last_refresh_attempt_at`, `last_refresh_success_at` and safe
`last_error` category/status/time data. Snapshots retain load time and optional
published time. Use monotonic clocks for TTL scheduling and UTC for diagnostics.
Stale/unverified snapshots with `usable=True` remain available.

Log loads and failures without payloads or exception URLs; ordinary hits should
not log at INFO. Enable `data_api.data.nthudata` INFO/DEBUG in the application's
logging configuration when diagnosing dataset behavior.

`GET /ping` and `HEAD /ping` inspect cached state only. Never fetch upstream,
refresh snapshots or call other endpoints from these handlers. Keep both out of
OpenAPI, preserve `Cache-Control: no-store`, and return no body for HEAD.
Return 200 when every dataset is usable (`ok` or `degraded`), or 503 when any
dataset is unavailable. Valid empty snapshots count as usable.

Keep `freshness` (last recorded refresh result) distinct from `check_due`
(TTL expired or never checked). Include all configured and additionally
registered datasets, use `null` for unknown metadata, and expose only safe error
category, upstream status and UTC time. `checked_at` is report time, not upstream
verification time. The detailed response contract is in the API guide.

This is readiness, not liveness. Never configure `/ping` as a Cloud Run startup
or liveness probe: only normal dataset requests retry failed startup loads after
the TTL. A traffic gate polling only `/ping` cannot recover a missing snapshot.
Readiness does not certify live energy/library integrations or MCP transport.

## CI Dependency Safety

The coverage uploader installs `.github/smokeshow-requirements.txt` with SHA-256
verification and wheels only, including transitive dependencies. To update it,
review `.github/smokeshow.in` and regenerate the lock:

```sh
uv pip compile .github/smokeshow.in --python-version 3.14 --universal --only-binary :all: --generate-hashes -o .github/smokeshow-requirements.txt
```

Review dependency and hash changes before merging. Preserve the uploader's
trusted default-branch checkout, artifacts from the exact successful push run,
and commit-SHA pins for checkout, Python setup and artifact Actions. Only the
upload job receives `statuses: write`. Preserve the 85% coverage threshold.

Test workflows and the Docker builder require source builds for the hash-locked
`jieba` source distribution and the local project. Do not disable all builds:
that breaks installation. Their existing Sonar build-script warnings remain
accepted risks, not eliminated vulnerabilities.

## Documentation

Keep `README.md` focused on project overview, public entry points, quick start
and contribution basics. Put consumer-facing query behavior and migration notes
in `docs/api-guide.md`; put agent workflow and internal maintenance constraints
here. Update the relevant guide when public behavior changes, instead of
appending implementation history to the README.

## Commit Message Guidelines

Use Conventional Commits for commit messages. Examples include:
- `feat: add new feature`
- `fix: fix a bug`
- `docs: reorganize documentation`