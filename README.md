# NTHU-Data-API
<p align="center">
    <em>NTHU-Data-API is a project designed for NTHU developers.</em>
    <br>
    <em>It provides an easy way to fetch data from the NTHU website.</em>
</p>
<p align="center">
<a href="https://github.com/psf/black" target="_blank">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
</a>
<a href="https://coverage-badge.samuelcolvin.workers.dev/redirect/NTHU-SA/NTHU-Data-API" target="_blank">
    <img src="https://coverage-badge.samuelcolvin.workers.dev/NTHU-SA/NTHU-Data-API.svg" alt="Test Coverage">
</a>
<a href="github.com/NTHU-SA/NTHU-Data-API/actions/workflows/tests.yml" target="_blank">
    <img src="https://github.com/NTHU-SA/NTHU-Data-API/actions/workflows/tests.yml/badge.svg" alt="Test Action Status">
</a>
<br>
<a href="https://sonarcloud.io/summary/new_code?id=NTHU-SA_NTHU-Data-API" target="_blank">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=NTHU-SA_NTHU-Data-API&metric=sqale_rating" alt="
Maintainability Rating">
</a>
<a href="https://sonarcloud.io/summary/new_code?id=NTHU-SA_NTHU-Data-API" target="_blank">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=NTHU-SA_NTHU-Data-API&metric=ncloc" alt="Lines of Code">
</a>
<a href="https://sonarcloud.io/summary/new_code?id=NTHU-SA_NTHU-Data-API" target="_blank">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=NTHU-SA_NTHU-Data-API&metric=sqale_index" alt="Technical Debt">
</a>
</p>

## Getting Started
### Prerequisites
Ensure you have Python 3.14 or later and [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.

### Installation
1. Clone the repository:
```sh
git clone https://github.com/NTHU-SA/NTHU-Data-API.git
```
2. Navigate to the project directory:
```sh
cd NTHU-Data-API
```
3. Create the virtual environment and install all dependencies:
```sh
uv sync --all-groups
```

### Configuration
Copy the environment template file and fill in your details:
```sh
cp .env.template .env
```

### Install Pre-commit Hooks (For Contributors)
To ensure code quality and consistency, we use pre-commit hooks. 
The pre-commit will automatically format your code before each commit. Install them by running:
```sh
uv run pre-commit install
```

### Running the Application
```sh
uv run python main.py
```

## Contributing
We follow certain guidelines for contributing. Here are the types of commits we accept:

- `feat: Add or modify features`
- `fix: Fix a bug`
... You can refer to the full list of commit types in the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.

### Search behavior
- MCP `search_courses` matches case-sensitive literal substrings in course titles,
  teacher names, and course IDs. Supplied filters are combined with AND; a keyword
  can match either the Chinese or English title. Regex characters such as `C++`
  and `[AI]` are treated literally. `limit` defaults to 20 and must be 1-100;
  zero, negative, and larger values are rejected.
- REST `GET /courses/search` retains regular-expression matching and ANDs the
  supplied fields. `POST /courses/search` retains nested AND/OR conditions and
  exact matching unless `regex_match` is true. Invalid regex syntax returns HTTP
  422, including when the course dataset is empty.
- MCP `find_dining` applies building and restaurant-name fuzzy filters together
  with `check_open`, before limiting results. Open-status remains based on the
  existing schedule-note heuristic, not a guarantee that a restaurant is open.
- The exported REST/MCP app applies CORS and returns `X-Process-Time`. CORS
  exposes `X-Total-Count`, `X-Data-Commit-Hash`, and `X-Process-Time` to browser
  clients from configured origins.

### Response schemas

Nullable metadata in announcements, newsletters, department contacts, dining
images, and library feeds/calendars may be omitted by publishers. These fields
default to `null` in REST responses; supplied values still undergo validation.
Required identifiers, titles not declared nullable, event boundaries, and dataset
structure remain required. Course GET search retains the same flat optional query
parameters, with validation errors documented in OpenAPI.

Library RSS article `link` is nullable text: a single URL or comma-separated list
of complete URLs is retained verbatim. Image `url` remains a validated HTTP(S)
URL; spaces in its path are encoded as `%20` before the candidate snapshot is
installed, without double-encoding existing escapes. This normalization is
RSS-specific and preserves every article and other upstream fields.

### Dining queries

`GET /dining/` supports optional `building_name`, `restaurant_name`, `fuzzy`
(default `true`), and `schedule` parameters. All supplied filters are combined
with AND. `schedule` accepts `today`, `weekday`, `saturday`, or `sunday`; omitting
it applies no opening-day filter. Invalid or empty schedule values return 422.

For example, find potentially open restaurants in a building today:

```text
/dining/?building_name=小吃部&schedule=today
```

The response is always a list of buildings with nested `restaurants`, regardless
of whether `schedule` is supplied. With a schedule filter, buildings with no
matching restaurants are omitted; no matches return `[]`. Without it, existing
search behavior is unchanged. With `fuzzy=false`, building names use exact
matching and restaurant names use case-sensitive literal substring matching.

`today` uses the **Asia/Taipei** date: Monday-Friday maps to `weekday`, with
separate Saturday and Sunday categories. Filtering only excludes restaurants
whose notes indicate a closure on that day. It does not check current opening
hours, holidays, or live availability. MCP `find_dining(check_open="today")`
uses the same Taiwan-date interpretation and retains its existing response
format and limits.

**Breaking change:** `/dining/open` has been removed, without a redirect or
compatibility alias. Replace `/dining/open?schedule=today` with
`/dining/?schedule=today`. The old endpoint returned a flat restaurant list;
clients must now read each building's `restaurants` (or flatten them locally).

### CI dependency safety

The coverage uploader installs from `.github/smokeshow-requirements.txt` with
SHA-256 verification and wheels only, including all transitive dependencies.
To update it, review the version in `.github/smokeshow.in` and regenerate the lock:

```sh
uv pip compile .github/smokeshow.in --python-version 3.14 --universal --only-binary :all: --generate-hashes -o .github/smokeshow-requirements.txt
```

Review dependency and hash changes before merging. The uploader checks out its
trusted default-branch revision, downloads artifacts from the exact successful push
run, and pins checkout, Python setup, and artifact Actions to commit SHAs. Only the upload job receives
`statuses: write`; the 85% coverage threshold remains unchanged.

The test workflows and Docker builder still need source builds for the
hash-locked `jieba` source distribution and the local project. Their existing
Sonar build-script warnings remain accepted risks, not eliminated vulnerabilities;
disabling all builds would break installation.

### Campus calendars

Campus calendars are loaded from `https://data.nthusa.tw/calendars.json` through
the shared dataset cache. The current calendar id is `academic`; use the list
endpoint to discover additional calendars as they are published.

| Endpoint | Response |
| --- | --- |
| `GET /calendars/` | All calendar metadata, without events |
| `GET /calendars/{calendar_id}` | One calendar's metadata, without events |
| `GET /calendars/{calendar_id}/events` | Filtered, paginated events |
| `GET /calendars/{calendar_id}/events/{event_id}` | One event |

For example, get academic events overlapping October 2026:

```text
/calendars/academic/events?start=2026-10-01&end=2026-10-31&limit=100&offset=0
```

- `start` and `end` are optional inclusive dates (`YYYY-MM-DD`), interpreted using
  the local dates in the source calendar (`Asia/Taipei` for `academic`). Events
  overlapping any part of the range are included, not just events starting in it.
  All-day event `end` values remain exclusive, as in the source; a timed event
  ending at midnight does not cover the following day.
- `keyword` is an optional case-insensitive literal substring in the title or
  description. Whitespace is trimmed; blank keywords apply no filter. All
  supplied filters are combined with AND.
- Events are sorted by `start`, then `id`. `limit` defaults to 100 (1-1000);
  `offset` defaults to 0 (nonnegative). `X-Total-Count` reports the filtered count
  before pagination; `X-Data-Commit-Hash` identifies the snapshot when known.
- Missing calendars/events return 404, reversed date ranges return 400, and
  malformed dates or invalid pagination return 422. No matches return `[]`.
  Unavailable data without a usable snapshot returns 503; refresh failures retain
  the last-known-good snapshot.

### Running Tests
To run tests locally before committing changes, follow these steps:
1. Install the required dependencies:
```sh
uv sync --group test
```
2. Run tests:
Navigate to the project's root directory and execute:
```sh
uv run --group test pytest -n auto tests
```
3. Generate a coverage report (optional):
If you need a test coverage report, run:
```sh
uv run --group test pytest -n auto tests --cov=src --cov=tests --cov-report=xml --cov-report=html:coverage --cov-fail-under=85
```

### Dataset lifecycle on Cloud Run

The published datasets at `NTHU_DATA_URL` are the persistent source of truth.
Each application process owns disposable in-memory snapshots, per-dataset async
locks, freshness/error metadata, and one HTTPX client managed by its lifespan.
REST and MCP share these services, including transformed courses and bus indexes.
Multiple workers in one container are also independent processes.

Requests drive refresh; there is no permanent background refresh loop, disk cache,
distributed lock, or cross-instance cache synchronization. Startup attempts to
prefetch all published datasets, including maps and library data, so readiness
can succeed before user traffic. Successful prefetch is not a requirement for
serving requests. An unavailable dataset does not prevent the application or
other datasets from starting.

- `FILE_DETAILS_CACHE_EXPIRY` (positive seconds, default **300**) controls freshness
  checks. Within the TTL, requests use the active snapshot without upstream access.
  The manifest is shared across datasets; reusing it does not extend its freshness.
  After expiry, one caller per dataset checks the version while concurrent callers
  wait and re-check the state. Unrelated dataset downloads do not block each other.
- A known matching version avoids downloading the dataset. A changed or previously
  unknown active version triggers download, checksum verification when supplied,
  validation, and complete transformation before atomic installation. Valid `[]`
  or `{}` replaces older records for datasets whose schema accepts that shape.
- A manifest failure or unknown expected version retains existing data as
  **unverified**. With no snapshot, direct loading is attempted and remains
  unverified. Unknown versions are never considered a confirmed match.
- Failed downloads, invalid schemas, or failed transformations preserve the
  last-known-good snapshot as **stale**, with bounded retry attempts (one per TTL,
  including failed cold starts). Cancellation does not prevent subsequent retries.
  There are no automatic HTTP retries.
- With no usable snapshot, REST returns **503** and MCP returns a controlled tool
  error, not a successful empty result. Valid empty datasets still succeed. Missing
  version metadata does not imply missing data: `X-Data-Commit-Hash` is omitted when
  unknown rather than inventing a version. Endpoint names and response bodies are
  otherwise unchanged, including existing not-found behavior.
- `DATA_HTTP_TIMEOUT` (positive seconds, default **15**) sets the pooled dataset
  client's HTTPX connect/read/write/pool timeouts. Shutdown closes the client,
  including when startup fails.

Last-known-good is an **instance-local availability optimization**, not durable
storage. Instances can temporarily serve different versions within the freshness
window. Restart/scale-to-zero loses the snapshot; a new instance must load upstream
data and can return 503 if that is unavailable. No cache survives via the container
filesystem.

#### Published manifest contract

The API consumes `file_details.json` in the publisher's existing shape:

```json
{
  "file_details": {
    "/": [
      {
        "name": "courses.json",
        "last_commit": "opaque-version",
        "last_updated": "2026-09-27T22:24:37+08:00"
      }
    ],
    "libraries": [
      {"name": "rss.json", "version": "opaque-version"}
    ]
  }
}
```

Section plus `name` identifies the dataset path. `last_commit` is preferred for
compatibility; `version` is a fallback. The current publisher also supplies an
optional lowercase `sha256` digest of file bytes. When present, it prevents a
manifest/data publication race from installing bytes under the wrong version.
Legacy manifests without a checksum remain supported but cannot provide this
integrity guarantee. Versions are opaque equality tokens, not sortable revisions.

`last_updated` is optional source metadata, not the local load/check time.
Extra fields are ignored; missing entries/versions mean unverified freshness.
Malformed entries, duplicate paths, and malformed manifests fail the check safely;
previous manifest entries are not reused as evidence of a successful new check.
No publishing pipeline change is required.

#### Availability and diagnostics

`app.state.datasets.states` exposes internal per-dataset `snapshot`, `usable`,
`freshness`, `last_checked_at`, `last_refresh_attempt_at`,
`last_refresh_success_at`, and safe `last_error` category/status/time information.
Snapshots separately retain load time and optional published time. TTL scheduling
uses a monotonic clock; diagnostic timestamps use UTC.

These distinguish liveness from dataset readiness: stale/unverified data with
`usable=True` is still available. A cold unavailable dataset has `usable=False`.
Logs record loads and failures without payloads or exception URLs; ordinary hits
are not logged at INFO. Set the Python application's logging configuration to
enable `data_api.data.nthudata` INFO/DEBUG events when needed.

Live electricity, library space, and lost-and-found integrations are not published
datasets and retain their existing on-demand behavior and separate HTTP clients.
They are not covered by snapshot freshness or last-known-good guarantees.
Public per-object freshness/provenance metadata and product
changes to dining/bus semantics are deferred.

#### Readiness endpoint

`GET /ping` reports the current process's cached dataset health. It is excluded
from Swagger UI and `/openapi.json`. It never fetches upstream data, refreshes a
snapshot, or calls other API endpoints; responses have `Cache-Control: no-store`.

- HTTP **200** with `ready: true` means every dataset has a usable snapshot.
  `status` is `ok` when all recorded freshness values are `current` and no check
  is due, or `degraded` when usable data is stale, unverified, or due for a check.
- HTTP **503** with `ready: false` and `status: "unavailable"` means at least one
  dataset has no usable snapshot, including datasets not loaded yet. Valid empty
  snapshots count as usable.
- `checked_at` is the UTC report time, not an upstream verification time.
  `datasets` is keyed by published JSON path and includes `usable`, `freshness`,
  `check_due`, `version`, `loaded_at`, `published_at`, `last_checked_at`,
  `last_refresh_attempt_at`, `last_refresh_success_at`, and `last_error`.
  Errors expose only category, upstream HTTP status (when known), and UTC time;
  payloads, exception messages, and upstream URLs are not returned.
- `freshness` is the last recorded refresh result; `check_due` separately indicates
  that its TTL has expired or it has never been checked. Unknown metadata is `null`.
  The report includes all configured datasets, even before their first request,
  plus any additional datasets registered in the manager.

This is a **readiness**, not a liveness, check. Do not use it as a Cloud Run
startup/liveness probe. Failed startup loads are retried by normal dataset
requests after the TTL, not by `/ping`; a traffic gate that only calls `/ping`
cannot recover a missing snapshot by itself. Live energy, library space,
lost-and-found, and MCP transport health are not probed or certified by this
report. Multiple instances may report different cached states.

Tests use mock transports and injected clocks; the default suite blocks real
HTTPX network traffic. Lifecycle coverage is in `tests/test_data_manager.py` and
`tests/test_runtime_lifecycle.py`; existing REST/MCP query and middleware tests
remain in the suite.

## Credit
This project is maintained by NTHUSA 32nd.

## License
This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).

## Acknowledgements
Thanks to SonarCloud for providing code quality metrics:

[![SonarCloud](https://sonarcloud.io/images/project_badges/sonarcloud-white.svg)](https://sonarcloud.io/summary/new_code?id=NTHU-SA_NTHU-Data-API)