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

### MCP tool names and display titles

The MCP endpoint is `https://api.nthusa.tw/mcp` (local: `http://localhost:5000/mcp`).
Each tool explicitly declares a stable English `name` for calls and a Traditional
Chinese `title` for display. Clients that support tool titles can display these
labels; other clients may continue to display the English names. Internal Python
function renames must not change these public names.

| Tool name | Display title |
| --- | --- |
| `search_campus` | 搜尋校園資訊 |
| `get_bus_schedule` | 查詢公車時刻表 |
| `search_courses` | 搜尋課程列表 |
| `get_announcements` | 搜尋校園公告 |
| `find_dining` | 搜尋餐廳列表 |
| `get_library_info` | 查詢圖書館資訊 |
| `get_newsletters` | 搜尋電子報列表 |
| `get_energy_usage` | 查詢校園即時用電 |

### Search behavior
- MCP `search_courses` matches case-sensitive literal substrings in course titles,
  teacher names, and course IDs. Supplied filters are combined with AND; a keyword
  can match either the Chinese or English title. Regex characters such as `C++`
  and `[AI]` are treated literally. `limit` defaults to 20 and must be 1-100;
  zero, negative, and larger values are rejected.
- REST `GET /courses` uses regular-expression matching and ANDs the
  supplied fields. `POST /courses/query` supports nested AND/OR conditions and
  exact matching unless `regex_match` is true. Invalid regex syntax returns HTTP
  422, including when the course dataset is empty.
- MCP `find_dining` applies building and restaurant-name fuzzy filters together
  with `check_open`, before limiting results. Open-status remains based on the
  existing schedule-note heuristic, not a guarantee that a restaurant is open.
- The exported REST/MCP app applies CORS and returns `X-Process-Time`. CORS
  exposes `X-Total-Count`, `X-Data-Commit-Hash`, and `X-Process-Time` to browser
  clients from configured origins. Unexpected failures before a response starts,
  including dependency and response validation errors, retain CORS and timing
  headers.

### Response schemas

Nullable metadata in announcements, newsletters, department contacts, dining
images, and library feeds/calendars may be omitted by publishers. These fields
default to `null` in REST responses; supplied values still undergo validation.
Required identifiers, titles not declared nullable, event boundaries, and dataset
structure remain required. Course GET search retains the same flat optional query
parameters, with validation errors documented in OpenAPI.

### Root endpoint paths

Use root GET endpoints without a trailing slash: `/announcements`, `/calendars`,
`/departments`, `/dining`, `/locations`, and `/newsletters`. Both forms respond
directly without a redirect and retain the same query parameters, response schemas,
and data-version headers. The trailing-slash endpoints remain available for
compatibility but are marked **deprecated** in OpenAPI, with descriptions pointing
to their replacements. Existing operation IDs identify the slashless endpoints;
the deprecated aliases use a `Deprecated` suffix to keep operation IDs unique.

`GET /courses` already uses this convention; its deprecated `/courses/` endpoint
retains its existing all-courses behavior.

### Announcement queries

The supported announcement endpoints are `GET /announcements` for announcement
content and `GET /announcements/sources` for source metadata without articles.
Use the `department` fields in `/announcements/sources` to discover department
names; clients needing a unique department list can deduplicate those values.
The redundant `GET /announcements/lists/departments` endpoint is deprecated in
OpenAPI but remains available for compatibility. It still returns HTTP 200 with
a sorted, unique list of department names and the `X-Data-Commit-Hash` header
when available.

```text
GET /announcements
GET /announcements/sources
GET /announcements?department=教務處
GET /announcements?title=停電
GET /announcements?language=zh-tw
```

Announcement filters and the optional `department` filter on `/announcements/sources`
are unchanged.

### Live library and energy endpoints

Use `GET /libraries/lost-and-found` for library lost items and
`GET /energy/electricity` for realtime campus electricity usage.
The old paths remain available with the same response formats and error behavior,
but are marked **deprecated** in OpenAPI:

| Deprecated endpoint | Replacement |
| --- | --- |
| `GET /libraries/lost_and_found` | `GET /libraries/lost-and-found` |
| `GET /energy/electricity_usage` | `GET /energy/electricity` |

MCP tool names and arguments are unchanged.

### Course queries

The supported course endpoints are `GET /courses` for ordinary queries and
`POST /courses/query` for the complex query DSL. GET without filters returns
all courses; empty field values apply no filter. All supplied field filters and
the optional `type` filter are combined with AND.

```text
GET /courses
GET /courses?teacher=林福仁
GET /courses?chinese_title=服務
GET /courses?type=microcredits
GET /courses?type=xclass&teacher=林福仁
```

`type` accepts `microcredits` and `xclass`, using the same predefined conditions
as the legacy lists. Unknown or empty types return HTTP 422.

For nested AND/OR queries, send a condition object or a condition array to
`POST /courses/query`:

```json
[
  {"row_field": "teacher", "matcher": "黃", "regex_match": true},
  "or",
  {"row_field": "teacher", "matcher": "孫", "regex_match": true}
]
```

`regex_match` defaults to `false` (exact matching); set it to `true` for
substring or regular-expression matching. Responses remain arrays of courses,
with `X-Total-Count` and `X-Data-Commit-Hash` headers.

The old endpoints remain available but are marked **deprecated** in OpenAPI:

| Deprecated endpoint | Replacement |
| --- | --- |
| `GET /courses/` | `GET /courses` |
| `GET /courses/search` | `GET /courses` with the same field filters |
| `POST /courses/search` | `POST /courses/query` with the same body |
| `GET /courses/lists/{list_name}` | `GET /courses?type={list_name}` |

Legacy behavior is preserved: `GET /courses/` returns all courses, while
`GET /courses/search` without non-empty field filters returns `[]`. Migrating
the latter to an unfiltered `GET /courses` instead returns all courses.

### Newsletter queries

`GET /newsletters` supports optional `name`, `title`, and `fuzzy` (default
`true`) parameters. Name and article-title filters are combined with AND.
Fuzzy matching uses partial similarity with a threshold of 80, like announcements.
With `fuzzy=false`, names must match exactly and titles use case-sensitive literal
substring matching. Empty filters apply no filtering.

Responses retain source metadata and nested `articles`; a title filter removes
non-matching articles and sources with no matching articles. Without a title
filter, sources with empty article lists are retained. No matches return `[]`.

`GET /newsletters/sources` lists `name`, `link`, and `details` without articles.
Its optional `name` filter matches exactly. Both endpoints return the dataset's
`X-Data-Commit-Hash` when available.

```text
/newsletters/sources
/newsletters?name=教務處
/newsletters?name=教務處綜合教務組電子報&title=選課&fuzzy=false
```

`GET /newsletters/{newsletter_name}` remains available with its existing enum,
single-object response, and 404 behavior, but is **deprecated** in OpenAPI.
Migrate to `/newsletters?name={newsletter_name}&fuzzy=false`, which returns
a list (or `[]` if no source matches). No removal date has been set.

### Location queries

Use `GET /locations` to list all campus locations, or supply `name` to search
by name. `fuzzy` defaults to `true`; set `fuzzy=false` to require an exact
name match. Omitting `name` or passing an empty value returns all locations
regardless of `fuzzy`.

```text
GET /locations
GET /locations?name=台積館
GET /locations?name=台積館&fuzzy=false
```

Responses are arrays of locations with `name`, `latitude`, and `longitude`,
and include `X-Data-Commit-Hash` when available. No matches return HTTP 200
with `[]`.

The old search endpoint remains available but is marked **deprecated** in OpenAPI:

| Deprecated endpoint | Replacement |
| --- | --- |
| `GET /locations/search?query=...` | `GET /locations?name=...` |

Legacy search behavior is preserved: `/locations/search` requires `query` and
returns HTTP 404 when no locations match.

### Bus routes, stops, and schedules

The bus API exposes three resources:

| Endpoint | Purpose |
| --- | --- |
| `GET /buses/routes` | Campus route metadata |
| `GET /buses/stops` | All bus stops with names and coordinates |
| `GET /buses/schedule` | Timetable query, optionally filtered by stop |

`GET /buses/stops` replaces `/buses/info/stops`. The old path remains available
with the same response format, is deprecated in OpenAPI, and will be removed
in the next major release. Stop-specific timetable queries use
`GET /buses/schedule?stop=台積館`, not a stop resource path.

Use `GET /buses/routes?route=main` to select campus route metadata. Its optional
`route` (`main`, `nanda`) and `direction` (`up`, `down`) filters return all routes
and directions when omitted. The query parameter `bus_type` is replaced by `route`.

Use `GET /buses/schedule` with optional `route` (`main`, `nanda`, `all`),
`day` (`weekday`, `weekend`, `current`), and `direction` (`up`, `down`, `all`).
Defaults are `route=all`, `day=current`, and `direction=all`, so a request without
parameters returns the next departures across all routes and directions.
`route` selects a campus route; response `bus_type` identifies the vehicle type
(for example, `large-sized_bus`), not the campus route.
Optional `stop` filters to buses serving that stop, without changing the response
format. `details=false` (default) returns departure schedules; `details=true`
includes `dep_info` and all `stops_time` entries. `time` filters by departure time
in HH:MM format, even when `stop` is supplied. `day=current` uses the current day
and time and ignores `time`. `limit` defaults to 5 and must be at least 1.
The shared `BusQuery` parameter is now `limit`, not `limits`, including on
deprecated bus endpoints; update clients to use the singular spelling.
Stop and time filters are applied before the limit; no matches return `[]`.

```text
/buses/schedule
/buses/schedule?stop=台積館
/buses/schedule?route=main&direction=up
/buses/schedule?route=main&limit=5
/buses/schedule?route=all&day=weekday&direction=up&stop=台積館&details=true
```

`GET /buses/schedules` and `GET /buses/stops/{stop_name}` remain available but are
deprecated in OpenAPI and will be removed in the next major release. Migrate to `/buses/schedule` and
`/buses/schedule?stop={stop_name}&details=true`, respectively, and rename query
`bus_type` to `route`. Both legacy endpoints retain their required `bus_type`,
`day`, and `direction` parameters. The old stop endpoint
retains its arrival-based response and time filtering; the new endpoint always
filters by departure time.

MCP `get_bus_schedule` replaces `get_next_buses` and `get_bus_stops` without
compatibility aliases. It accepts `route`, `direction`, `limit`, `stop`, `day`,
`time`, and `details`, using the same schedule filters as REST. Defaults are
`route=all`, `direction=all`, `day=current`, `limit=5`, and `details=true`.
Its `buses` list uses the REST schedule format; `stop_name` and `stop_info`
(including coordinates) are included when `stop` is supplied. MCP clients must
refresh their tool list and use the new name and response format.
If supplied, MCP `time` must be a zero-padded HH:MM value from `00:00` to `23:59`;
malformed values are rejected during argument validation, even for `day=current`.

### Dining queries

`GET /dining` supports optional `building_name`, `restaurant_name`, `fuzzy`
(default `true`), and `schedule` parameters. All supplied filters are combined
with AND. `schedule` accepts `today`, `weekday`, `saturday`, or `sunday`; omitting
it applies no opening-day filter. Invalid or empty schedule values return 422.

For example, find potentially open restaurants in a building today:

```text
/dining?building_name=小吃部&schedule=today
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
`/dining?schedule=today`. The old endpoint returned a flat restaurant list;
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

Campus and library calendars share the same endpoints and response schemas.
The API combines `https://data.nthusa.tw/calendars.json` and
`https://data.nthusa.tw/libraries/calendars.json` through the shared dataset cache;
no publisher changes are required. Campus ids such as `academic` are unchanged.
Library source ids `main`, `hss`, and `nanda` become `library-main`, `library-hss`,
and `library-nanda`. Use the list endpoint to discover available calendars.

Calendar metadata includes optional `category`, `source`, and `url` fields.
Library calendars have `category: "library"` and `source: "NTHU Library"`, and
retain their source calendar URL. Other calendars preserve publisher-supplied
metadata; missing optional metadata is `null`. Future campus calendars can add
categories and sources without new routers. The `library-` namespace is reserved
for library calendars; duplicate ids within a dataset are rejected.

| Endpoint | Response |
| --- | --- |
| `GET /calendars` | All calendar metadata, without events |
| `GET /calendars/{calendar_id}` | One calendar's metadata, without events |
| `GET /calendars/{calendar_id}/events` | Filtered, paginated events |
| `GET /calendars/{calendar_id}/events/{event_id}` | One event |

For example, get academic events overlapping October 2026:

```text
/calendars/academic/events?start=2026-10-01&end=2026-10-31&limit=100&offset=0
```

Library opening hours use the same query parameters:

```text
/calendars/library-main/events?start=2026-10-01&end=2026-10-31
```

**Breaking change:** All four `/libraries/calendars` endpoints have been removed,
without deprecated routes, redirects, or compatibility aliases. Migrate to
`/calendars` and `/calendars/library-{main,hss,nanda}` with the same event paths.

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
  before pagination. For individual calendars/events, `X-Data-Commit-Hash` is
  the source dataset's version. For the combined list, it is the SHA-256 of the
  JSON-encoded `[campus_version, library_version]` array, and is omitted if either
  version is unknown.
- Missing calendars/events return 404, reversed date ranges return 400, and
  malformed dates or invalid pagination return 422. No matches return `[]`.
  Unavailable data without a usable snapshot returns 503; refresh failures retain
  the last-known-good snapshot.
- The list requires usable snapshots for both datasets and returns 503 rather
  than a partial list if either is unavailable. Individual calendar/event requests
  only load their own source, so an outage in the other source does not block them.

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
prefetch published datasets used by REST/MCP, including maps, library RSS, and
library calendars, so readiness can succeed before user traffic. The unpublished
root `libraries.json` is not a required dataset. Successful prefetch is not a
requirement for serving requests. An unavailable dataset does not prevent the
application or other datasets from starting.

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
Their REST endpoints return **502** for upstream connection/HTTP failures or
invalid JSON/HTML/data, and **504** for upstream timeouts. Unexpected internal
errors return **500**. Error bodies retain a `detail` field with fixed, safe
messages; upstream URLs and exception details stay in server logs. These responses
and their JSON schema are documented in OpenAPI. MCP live tools report failures
as tool errors (`isError: true`), not successful `{"error": ...}` results.
Valid empty space lists and lost-item results still succeed. Lost-item pages must
contain exactly the expected table columns (in any order, without duplicates) or
the library's explicit empty-result message on its lost-and-found page. Unexpected
columns, missing tables, and malformed rows are upstream errors.
Public per-object freshness/provenance metadata and product
changes to dining/bus semantics are deferred.

#### Readiness endpoint

`GET /ping` reports the current process's cached dataset health. It is excluded
from Swagger UI and `/openapi.json`. It never fetches upstream data, refreshes a
snapshot, or calls other API endpoints; responses have `Cache-Control: no-store`.

`HEAD /ping` supports uptime monitors such as UptimeRobot. It uses the same
readiness status codes as GET (200 or 503), returns no body, and retains
`Cache-Control: no-store`. It is also excluded from the API schema and never
fetches upstream data.

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