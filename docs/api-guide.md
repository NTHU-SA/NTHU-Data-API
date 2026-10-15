# API Guide

[Back to README](../README.md)

This guide is for REST and MCP consumers. Start with discovery and shared query
conventions, then use the resource sections for examples. Existing clients should
read the [3.0 migration guide](migration-3.0.md) before upgrading. For local setup
and validation, see the [development guide](development.md).

The examples below use paths relative to `https://api.nthusa.tw` (local:
`http://localhost:5000`). See [Swagger UI](https://api.nthusa.tw/docs) for
complete request and response schemas.

## Contents

| Task | Read |
| --- | --- |
| Connect to REST or MCP | [Discovery and MCP](#discovery-and-mcp) |
| Understand paths, filters, responses and headers | [Query conventions](#query-conventions) |
| Upgrade an existing client | [Version policy](#version-policy-and-30-migration) and [3.0 migration guide](migration-3.0.md) |
| Handle unavailable data or check readiness | [Availability and readiness](#availability-and-readiness) |

### Query reference

| Resource | Main endpoints | Details |
| --- | --- | --- |
| Courses | `/courses`, `/courses/semesters`, `/courses/{semester}` | [Semester selection](#semester-selection), [GET filters](#get-filters), [POST query DSL](#post-query-dsl), [MCP](#course-mcp-query) |
| Directory | `/directory` | [Department and people matching](#directory-queries) |
| Announcements | `/announcements`, `/announcements/sources` | [Source and content filters](#announcement-queries) |
| Newsletters | `/newsletters`, `/newsletters/sources` | [Source and article filters](#newsletter-queries) |
| Locations | `/locations` | [Name matching](#location-queries) |
| Buses | `/buses/routes`, `/buses/stops`, `/buses/schedule` | [Routes and stops](#bus-routes-and-stops), [schedule filters](#bus-schedule-filters), [MCP](#bus-mcp-query) |
| Dining | `/dining` | [Name and schedule filters](#dining-queries) |
| Library and energy | `/libraries/spaces`, `/libraries/lost-and-found`, `/libraries/rss/{rss_type}`, `/energy/electricity` | [Live queries](#live-library-and-energy-endpoints), [RSS](#library-rss) |
| Calendars | `/calendars`, `/calendars/{calendar_id}/events` | [Calendar selection](#campus-calendars), [event filters](#calendar-event-filters) |

## Discovery and MCP

### API metadata

`GET /` returns a small discovery response without reading datasets or making
upstream requests. The name and version match the FastAPI application metadata.

```json
{
  "name": "NTHU Data API",
  "version": "3.0.0",
  "docs": "/docs",
  "openapi": "/openapi.json",
  "mcp": "/mcp"
}
```

The endpoint is hidden from OpenAPI and Swagger UI. Use `/ping` for dataset readiness checks;
the metadata endpoint does not indicate dataset readiness.

### MCP tool names and display titles

The MCP endpoint is `https://api.nthusa.tw/mcp` (local: `http://localhost:5000/mcp`).
Each tool explicitly declares a stable English `name` for calls and a Traditional
Chinese `title` for display. Clients that support tool titles can display these
labels; other clients may continue to display the English names.

| Tool name | Display title |
| --- | --- |
| `search_directory` | 搜尋清華通訊錄 |
| `search_locations` | 搜尋校園地點 |
| `get_bus_schedule` | 查詢公車時刻表 |
| `search_courses` | 搜尋課程列表 |
| `get_announcements` | 搜尋校園公告 |
| `find_dining` | 搜尋餐廳列表 |
| `get_library_info` | 查詢圖書館資訊 |
| `get_newsletters` | 搜尋電子報列表 |
| `get_energy_usage` | 查詢校園即時用電 |

## Version policy and 3.0 migration

The service runs **one live version**, without versioned URL prefixes or
per-request version selection. A release tag identifies deployed source, not an
independently supported API. Minor and patch releases preserve public REST/MCP
contracts; prefer adding optional filters or metadata over renaming endpoints.
Clients should tolerate extra response fields and discover dataset-backed values
instead of treating examples as exhaustive lists.

Deprecation is advance notice, not permission to remove an interface in a minor
release. Future deprecations must document a replacement and migration differences,
appear in OpenAPI/tool documentation as applicable, and be announced before removal
in a major release. Necessary security or correctness fixes may be exceptions and
must explicitly describe their impact. Removing an endpoint is still a breaking
change even after deprecation; there is no promise that old clients keep working
after a major upgrade.

**3.0.0 is being prepared and includes breaking changes.** Endpoint replacements,
course field mappings and MCP client changes are collected in the
[3.0 migration guide](migration-3.0.md). The unreleased contracts may change before
the first stable tag; after publication, the compatibility policy above applies.

## Query conventions

### Root endpoint paths

Use root GET endpoints without a trailing slash: `/announcements`, `/calendars`,
`/dining`, `/locations`, and `/newsletters`. Only slashless operations are
registered and documented. Trailing-slash requests use the framework's automatic
307 redirect, not separate compatibility endpoints. `GET /courses` and
`GET /directory` follow the same convention.

### Search behavior

Matching rules are resource-specific, not interchangeable. In particular:

| Query | Matching |
| --- | --- |
| Course REST GET | Regex for text; exact native values for numeric/boolean fields |
| Course REST POST | Typed exact matching by default; opt-in text regex and nested AND/OR |
| Course MCP | Case-sensitive literal substrings, not regex |
| Dining | Fuzzy name matching by default; schedule notes are not live availability |

The resource sections below document defaults, empty-filter behavior and limits.
Apply all filters before result limits. Invalid course regex returns 422 even
when the dataset is empty.

### Response headers and CORS

The exported REST/MCP app applies CORS and returns `X-Process-Time`. CORS
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

Snapshot-backed endpoints document HTTP 503 with `{"detail": "..."}` when no
usable snapshot exists. Manual 400/404 errors use the same string-detail schema.
Course 422 responses allow either FastAPI's validation-error array in `detail`
or a string for invalid GET regular expressions. OpenAPI success responses declare
`X-Data-Commit-Hash` where supplied (omitted for unknown versions), and
`X-Total-Count` on course responses and paginated calendar event lists.

## Directory queries

The documentation groups these endpoints under `Directory`.
Use `GET /directory` to retrieve the directory, or `GET /directory?query=...`
to match department names, people names, or titles. The optional `fuzzy` boolean
defaults to `true`. Set `fuzzy=false` for case-sensitive full-string equality
against any of those fields, not substring or regular-expression matching.
For example, `/directory?query=王小明&fuzzy=false` matches that full person name.
An omitted or empty `query` returns the entire directory; no matches return an
empty array.
The response is always a list of the existing `Department` model. A department
name match returns that department in full. When only its people match, the
department metadata is retained and `details.people` contains only matching
people. Fuzzy results are sorted by match score, while nested people retain their
dataset order; exact results retain dataset order. Filtering does not modify the
cached dataset.

MCP `search_directory(query, fuzzy=true)` uses the same matching fields and modes
but returns separate `departments` and `people` arrays, capped at 5 departments
and 10 people after filtering and ranking. A department-name match does not
automatically include its people in the separate people array. It does not search
locations. A valid empty result is `{departments: [], people: []}`; an unavailable
dataset is a tool error.
The tool loads only the directory dataset, independently of location searches.

## Announcement queries

The supported announcement endpoints are `GET /announcements` for announcement
content and `GET /announcements/sources` for source metadata without articles.
The sources response is a `list[AnnouncementSource]` with required `title`, `link`
(HTTP/HTTPS URL), `language`, and `department` fields, documented in OpenAPI.
Use the `department` fields in `/announcements/sources` to discover department
names; clients needing a unique department list can deduplicate those values.

```text
GET /announcements
GET /announcements/sources
GET /announcements?department=教務處
GET /announcements?title=停電
GET /announcements?language=zh-tw
GET /announcements?url=academic.site.nthu.edu.tw
GET /announcements?url=academic.site.nthu.edu.tw/p/403-1007-1504-1.php
```

The optional `url` query parameter filters announcement sources by a substring of
their `link`, ignoring `http://` and `https://` in both the query and source link.
HTTP(S) schemes and hostnames match case-insensitively; paths, queries, and
fragments remain case-sensitive. It accepts a domain or a URL with a path,
combines with the other filters, and does not use fuzzy matching regardless of
the `fuzzy` setting. It does not filter individual article links. Existing filters
and the optional `department` filter on `/announcements/sources` are unchanged.

## Library and energy

### Live library and energy endpoints

Use `GET /libraries/spaces` for the library space availability collection
(`list[LibrarySpace]`), `GET /libraries/lost-and-found` for library lost items, and
`GET /energy/electricity` for realtime campus electricity usage.
For failure status codes and MCP tool errors, see
[live integration errors](#live-integration-errors).

### Library RSS

`GET /libraries/rss/{rss_type}` accepts `news`, `eresources`, `exhibit`, or
`branches`. Each response is an article array. Article `link` is nullable **text**,
not a single URI: publishers may supply multiple comma-separated URLs, and the
API preserves the complete text. Consumers must not assume that the value can be
opened as one URL.

Image `url` and `link` remain nullable HTTP(S) URLs. RSS image URL path spaces are
encoded as `%20` before validation, without double-encoding existing escapes;
protocol-relative images use HTTPS. This normalization applies to the complete
installed RSS candidate and does not weaken URL validation for other datasets.
An invalid candidate retains the last-known-good snapshot; with no usable snapshot,
requests return 503. A missing feed returns 404 and an invalid `rss_type` returns 422.

## Course queries

### Semester selection

| Endpoint | Dataset or purpose |
| --- | --- |
| `GET /courses/semesters` | Discover published semester codes |
| `GET /courses` | Latest courses with GET filters |
| `POST /courses/query` | Latest courses with a query body |
| `GET /courses/{semester}` | Selected semester with GET filters |
| `POST /courses/{semester}/query` | Selected semester with a query body |

`GET /courses` and `POST /courses/query` use the publisher's
`courses/latest.json`. They do not infer a semester from today's date or the
largest published semester code. Select a semester with `GET /courses/{semester}`
or `POST /courses/{semester}/query`. Every course operation returns an array
of the same normalized course objects.

`GET /courses/semesters` returns five-digit semester codes, newest first, from
the published `courses/sources.json` catalog:

```json
["11510", "11420", "11410"]
```

This is a shortened example, not the complete list. Discover available semesters
rather than hardcoding them. `11510` means academic year 115, first semester;
the path uses the complete publisher code without shortening it to `1151`.

Malformed codes return **422**; well-formed, unpublished semesters return **404**.
An unavailable catalog or course dataset with no usable snapshot returns **503**.
A stale/unverified catalog cannot establish that an absent semester is unpublished:
that case returns 503 instead of 404. Known entries may still use usable snapshots.
There is no fallback to another semester or to latest.

Course and semester-list responses include `X-Total-Count` and, when known,
`X-Data-Commit-Hash` for the specific file used. latest and a named semester can
have different contents and versions even when their semester codes agree.

### GET filters

GET without filters returns all courses; empty text filters apply no filter.
All supplied field filters and the optional `type` filter are combined with AND.
Text filters use regex; numbers and booleans use exact typed equality. Zero and
false are real filters, not missing values. Unknown query parameters are rejected
with 422.

```text
GET /courses
GET /courses/semesters
GET /courses/11510
GET /courses/11510?lecturers.name_zh=林福仁
GET /courses/11420?lecturers.label=林福仁
GET /courses?chinese_title=服務
GET /courses?language_code=zh%7Cen
GET /courses/11510?credits=3&is_cancelled=false
GET /courses/11510?meetings.time_codes=M3
GET /courses?type=microcredits
GET /courses?type=xclass&lecturers.name_zh=林福仁
```

`type` accepts `microcredits` (credits with a fractional part, such as 0.5 or 1.5;
not integer credits or null) and `xclass` (case-sensitive `X-Class` in `note`).
Unknown or empty types return HTTP 422.
`language_code` is a text regex filter (for example, `zh|en`); published
course values remain limited to `zh`, `en`, or null.

Nested filters use leaf paths: `lecturers.label`, `lecturers.name_zh`,
`lecturers.name_en`, `meetings.classroom`, `meetings.time`, `meetings.time_codes`,
`expertises.name`, `expertises.type`, `curriculum_requirements.target`, and
`curriculum_requirements.requirement`. `programs` and `parsing_issues` match
individual string elements. Array predicates match **any** element. Two ANDed
predicates may match different objects in the same array; same-object grouping
is not supported. Missing teacher-union keys do not count as null values.

### POST query DSL

For nested AND/OR queries, send a condition object or a condition array to
`POST /courses/query` or `POST /courses/11510/query`:

```json
[
  {"row_field": "lecturers.name_zh", "matcher": "黃", "regex_match": true},
  "or",
  {"row_field": "lecturers.name_zh", "matcher": "孫", "regex_match": true}
]
```

`regex_match` defaults to `false` (exact matching). `matcher` must have the
field's native type: `{"row_field":"credits","matcher":3}`,
`{"row_field":"is_cancelled","matcher":false}`, or
`{"row_field":"language_code","matcher":null}`. Null only matches an explicitly
unknown nullable value, not a missing union key, empty array, empty string,
zero or false. GET does not have a special `"null"` query value.

Set `regex_match` to `true` only with a string matcher and a text field/leaf.
Wrong matcher types and regex applied to non-text fields return 422, including
on empty datasets. Numeric comparisons other than equality are not supported.

A condition object may also be wrapped in a single-element array. Every non-empty
array, including nested arrays, must have an odd number of elements alternating
between conditions (objects or arrays) and the lowercase operators `"and"` or
`"or"`. Operators are evaluated left to right with no implicit AND precedence;
use nested arrays to group expressions. An empty array `[]` matches all courses,
including when used as a nested operand.

Queries allow at most **32 array levels** (the outermost array is level 1) and
**1,024 nodes** across the whole tree. Each array, condition object and operator
counts as one node; fields inside condition objects do not count separately.
Malformed grammar, exceeded limits and invalid regex syntax return HTTP 422,
even when the course dataset is empty.

### Normalized fields and 3.0 migration

All course objects expose 33 fields. Numeric and boolean metadata may be null;
missing source information is not silently converted to zero, false or Chinese.
Arrays remain arrays, including empty arrays. For old-to-new field mappings,
see the [course migration table](migration-3.0.md#course-fields-and-queries);
old field names are not aliases. Swagger UI defines the complete response schema.

`credits` is a nullable nonnegative number; `capacity` and `reserved_for_freshmen`
are nullable nonnegative integers; `capacity_unlimited` and `is_cancelled` are
nullable booleans. `language_code` is `"zh"`, `"en"` or null.
`lecturers`, `meetings`, `expertises`, `programs` and `curriculum_requirements`
are arrays; `prerequisite_text` is a string.

`object` is the course audience/enrollment restriction, `ge_type` is the
general-education audience, and `ge_category` is its category.

Additional fields are `semester_code`; nullable text `department_code`,
`course_number`, `department_name`, `college_name`, `course_level_code`,
`course_level`, `remote_teaching`; nullable nonnegative integers `enrolled_count`,
`enrollment_after_selection`, `enrollment_after_withdrawal`; and string-array
`parsing_issues`. The three enrollment counts represent different source
measurements and must not be substituted for each other. A capacity of zero,
unlimited capacity and unknown capacity are distinct.

Teacher objects preserve their published shape. A historical `{label}` is not
guessed into Chinese and English names. Nested object values may be null;
`meetings.time_codes` may also be null when the publisher could not parse the
time text. Parser warnings are preserved, not repaired or used to reject otherwise
valid records. Required fields and invalid structures still fail snapshot
installation; an older usable snapshot is retained if available.

### Course MCP query

`search_courses` accepts `keyword`, `teacher`, `course_id`, `limit` and optional
`semester`. Filters use case-sensitive literal substrings and are combined with
AND. A keyword can match either the Chinese or English course title; `teacher`
matches label, Chinese or English lecturer names. Regex characters such as `C++`
and `[AI]` are treated literally. `limit` defaults to 20 and must be 1-100;
zero, negative and larger values are rejected.

The result is `{count, courses}`, with complete normalized course objects.
Semester failures are tool errors, not successful empty results.

### Snapshot loading

Startup loads latest and the semester catalog. Historical semesters load on
demand, using independent snapshots and refresh locks. REST and MCP in the same
app share these snapshots; switching semesters does not change other requests'
data. A failed refresh may serve only that dataset's last-known-good snapshot.
`/ping` includes lazily registered semester datasets, so a requested semester
without a usable snapshot also affects readiness. Polling readiness alone does
not trigger recovery.

## Newsletter queries

### REST newsletter queries

`GET /newsletters` supports optional `name`, `title`, and `fuzzy` (default
`true`) parameters. Name and article-title filters are combined with AND.
Fuzzy matching uses partial similarity with a threshold of 60 for both names and
article titles, sharing the name-search logic with MCP `get_newsletters`.
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

### Newsletter MCP query

MCP `get_newsletters` accepts an optional `search` for fuzzy source-name matching
with the same threshold of 60. Omitted or empty searches return all sources.
It returns all matching sources in publisher order, without a source-count limit.
Each source contains `name`, `link`, and `latest_articles`, retaining at most the
first three articles in publisher order with their `title` and `date`.
`count` is the number of matching sources and always equals the length of
`newsletters`, not the number of articles. No matches return
`{"count": 0, "newsletters": []}`.

For changes from earlier matching rules and source limits, see
[newsletter migration](migration-3.0.md#newsletter-matching).

## Location queries

Use `GET /locations` to list all campus locations, or supply `name` to search
by name. `fuzzy` defaults to `true`; set `fuzzy=false` to require an exact
name match. Omitting `name` or passing an empty value returns all locations
regardless of `fuzzy`.

MCP `search_locations(query, fuzzy=true)` searches only locations and returns
`{locations}`, capped at 5 results after filtering and fuzzy ranking. Set
`fuzzy=false` for case-sensitive full-string name equality. Unlike the REST
listing endpoint, an empty MCP query does not request all locations. No matches
return `{locations: []}`; an unavailable dataset is a tool error. Use
`search_directory` for department or staff contacts instead.

```text
GET /locations
GET /locations?name=台積館
GET /locations?name=台積館&fuzzy=false
```

Responses are arrays of locations with `name`, `latitude`, and `longitude`,
and include `X-Data-Commit-Hash` when available. No matches return HTTP 200
with `[]`.

## Bus routes, stops, and schedules

The bus API exposes three resources:

| Endpoint | Purpose |
| --- | --- |
| `GET /buses/routes` | Campus route metadata |
| `GET /buses/stops` | All bus stops with names and coordinates |
| `GET /buses/schedule` | Timetable query, optionally filtered by stop |

### Bus routes and stops

Stop-specific timetable queries use
`GET /buses/schedule?stop=台積館`, not a stop resource path.

Use `GET /buses/routes?route=main` to select campus route metadata. Its optional
`route` (`main`, `nanda`) and `direction` (`up`, `down`) filters return all routes
and directions when omitted.

### Bus schedule filters

Use `GET /buses/schedule` with these optional parameters:

| Parameter | Values or purpose | REST default |
| --- | --- | --- |
| `route` | `main`, `nanda`, `all` | `all` |
| `day` | `weekday`, `weekend`, `current` | `current` |
| `direction` | `up`, `down`, `all` | `all` |
| `stop` | Only buses serving the named stop | No stop filter |
| `time` | HH:MM threshold; ignored for `day=current` | See time filtering below |
| `details` | Include `dep_info` and `stops_time` | `false` |
| `limit` | Result limit, at least 1 | `5` |

A request without parameters returns the next departures across all routes and
directions. The parameter is `limit`, not `limits`.
Stop and time filters are applied before the limit; no matches return `[]`.

### Bus response fields

`route` selects a campus route; response `bus_type` identifies the vehicle type
(for example, `large-sized_bus`), not the campus route. `details=false` returns
departure schedules; `details=true` includes `dep_info` and all `stops_time` entries.
Filtering by `stop` does not change the response format.

The REST endpoint and MCP use campus-qualified `line` identifiers:
`main_red`, `main_green`, `nanda_route_1`, and `nanda_route_2`. With `details=true`,
the identifier is in `dep_info.line`; otherwise it is in `line`.
Nanda route selection uses the publisher's explicit `line` (`route1`/`route2`),
including when `description` is empty. Only records without a line use the legacy
description heuristic. The same selection determines stop membership and arrival times.

### Bus time filtering

`time` is in HH:MM format and filters by estimated arrival time at the selected
`stop`, including buses that
have departed but have not arrived at that stop yet. Arrivals exactly at the
requested time are included; buses that have already passed the stop are excluded.
Without `stop`, filtering still uses departure time. Both detail modes use the
same time filter and retain departure-time ordering. `day=current` uses the
current day and time and ignores `time`.

```text
/buses/schedule
/buses/schedule?stop=台積館
/buses/schedule?route=main&direction=up
/buses/schedule?route=main&limit=5
/buses/schedule?route=all&day=weekday&direction=up&stop=台積館&details=true
```

### Bus MCP query

`get_bus_schedule` accepts `route`, `direction`, `limit`, `stop`, `day`,
`time`, and `details`, using the same schedule filters as REST. Defaults are
`route=all`, `direction=all`, `day=current`, `limit=5`, and `details=true`.
Its `buses` list uses the REST schedule format; `stop_name` and `stop_info`
(including coordinates) are included when `stop` is supplied.
If supplied, MCP `time` must be a zero-padded HH:MM value from `00:00` to `23:59`;
malformed values are rejected during argument validation, even for `day=current`.

## Dining queries

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
uses the same Taiwan-date interpretation.

### Dining MCP query

MCP `find_dining` always returns `{"buildings": [...]}`, with each building's
matching restaurants nested under `restaurants`, whether or not `check_open`
is supplied. Restaurant entries contain `name`, `phone`, `schedule`, and `note`
(empty notes become `null`). All filters apply before limiting results.
Without a non-empty `building` filter, each building includes at most 10
matching restaurants. Supplying `building` returns **all** matching restaurants
in every fuzzy-matched building, not just the first matching building.
Buildings with no matches are omitted; no matches return `{"buildings": []}`.
For example, `find_dining(building="水木", check_open="today")` lists all
restaurants matching the opening-day heuristic in matching buildings, using
the same grouped structure as a query without `check_open`.

MCP `find_dining` applies building and restaurant-name fuzzy filters together
with `check_open`, before limiting results.
For the previous response format and limits, see
[MCP client migration](migration-3.0.md#mcp-client-migration).

## Campus calendars

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

### Calendar event filters

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

## Availability and readiness

### Dataset snapshots

The published datasets at `NTHU_DATA_URL` are the persistent source of truth.
Each process keeps in-memory snapshots shared by REST and MCP. Requests drive
freshness checks, controlled by `FILE_DETAILS_CACHE_EXPIRY` (default 300 seconds).
Failed refreshes retain the last-known-good snapshot; without a usable snapshot,
REST returns **503** and MCP returns a controlled tool error. Valid empty datasets
still succeed, and unknown versions omit `X-Data-Commit-Hash`.

Dataset versions come only from each entry's `version` in `file_details.json`;
`last_commit` is ignored, including when `version` is missing or null. Versions
are opaque equality tokens. An unchanged version avoids downloading, while a
changed version triggers a download and validation. Optional `sha256` verifies
downloaded bytes; it is not a version identifier, and checksum-only changes do
not trigger a download. Missing or null versions retain an existing snapshot as
unverified; without a snapshot, a direct load is attempted and remains unverified.
The public `X-Data-Commit-Hash` header retains its name but carries the dataset
version (or the combined calendar version described above).

Snapshots are not durable or synchronized across instances. A restart or
scale-to-zero loses cached data, and different instances can temporarily serve
different versions. Startup prefetch failures do not prevent other datasets from
being served.

### Live integration errors

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

### Readiness endpoint

`GET /ping` reports the current process's cached dataset health. It is excluded
from Swagger UI and `/openapi.json`. It never fetches upstream data, refreshes a
snapshot, or calls other API endpoints; responses have `Cache-Control: no-store`.

`HEAD /ping` supports uptime monitors such as UptimeRobot. It uses the same
readiness status codes as GET (200 or 503), returns no body, and retains
`Cache-Control: no-store`. It is also excluded from the API schema and never
fetches upstream data.

| HTTP | `ready` | `status` | Meaning |
| --- | --- | --- | --- |
| 200 | `true` | `ok` | Every dataset is usable, recorded freshness is `current`, and no check is due |
| 200 | `true` | `degraded` | Every dataset is usable, but some data is stale, unverified or due for a check |
| 503 | `false` | `unavailable` | At least one dataset has no usable snapshot, including datasets not loaded yet |

Valid empty snapshots count as usable.

### Readiness report fields

`checked_at` is the UTC report time, not an upstream verification time.
`datasets` is keyed by published JSON path and includes `usable`, `freshness`,
`check_due`, `version`, `loaded_at`, `published_at`, `last_checked_at`,
`last_refresh_attempt_at`, `last_refresh_success_at`, and `last_error`.
Errors expose only category, upstream HTTP status (when known), and UTC time;
payloads, exception messages, and upstream URLs are not returned.

`freshness` is the last recorded refresh result; `check_due` separately indicates
that its TTL has expired or it has never been checked. Unknown metadata is `null`.
The report includes all configured datasets, even before their first request,
plus any additional datasets registered in the manager.

### Readiness limitations

This is a **readiness**, not a liveness, check. Do not use it as a Cloud Run
startup/liveness probe. Failed startup loads are retried by normal dataset
requests after the TTL, not by `/ping`; a traffic gate that only calls `/ping`
cannot recover a missing snapshot by itself. Live energy, library space,
lost-and-found, and MCP transport health are not probed or certified by this
report. Multiple instances may report different cached states.
