# 3.0 migration guide

[Back to API guide](api-guide.md) | [Release guide](releasing.md)

Use this guide to update existing REST and MCP clients. For current query
examples and response rules, use the [API guide](api-guide.md).

**3.0.0 is being prepared and includes breaking course changes.** The unreleased
contracts may be updated before the first stable tag. After publication, the
ordinary [major-version compatibility policy](api-guide.md#version-policy-and-30-migration)
applies.

## Contents

- [REST endpoint migration](#rest-endpoint-migration)
- [Course fields and queries](#course-fields-and-queries)
- [Newsletter matching](#newsletter-matching)
- [MCP client migration](#mcp-client-migration)

## REST endpoint migration

3.0.0 removes all previously deprecated REST operations. Existing supported
operation IDs remain unchanged. Removed paths have no compatibility handlers;
most return 404. `GET /courses/search` now matches the semester route and returns
422 for an invalid semester; POST at that path returns 405.

There are no custom legacy redirects. Ordinary FastAPI trailing-slash
normalization remains enabled: `/courses/` redirects to `/courses` with 307 and
preserves query parameters. It no longer has a separate operation or special
all-courses behavior.

| Removed operation | Replacement and migration difference |
| --- | --- |
| `GET /announcements/`, `/calendars/`, `/dining/`, `/locations/`, `/newsletters/` | Use the slashless collection URL directly to avoid a 307 redirect. |
| `GET /departments/` | `GET /directory`; same department collection model. |
| `GET /departments/search` | `GET /directory?query=...`; returns departments with matching nested people, not separate `departments`/`people` arrays. MCP `search_directory` retains its own separate arrays. |
| `GET /announcements/lists/departments` | `GET /announcements/sources`; extract and deduplicate `department` locally, sorting if needed. |
| `GET /courses/` | `GET /courses`; supplied filters now apply, including after a slash redirect. |
| `GET /courses/search` | `GET /courses` with the same field filters; no non-empty filters now returns **all courses**, not `[]`. |
| `POST /courses/search` | `POST /courses/query` with the same body. |
| `GET /courses/lists/{list_name}` | `GET /courses?type={list_name}`. |
| `GET /newsletters/{newsletter_name}` | `GET /newsletters?name={newsletter_name}&fuzzy=false`; returns an array, or `[]` instead of 404. Names are no longer restricted to a fixed legacy enum. |
| `GET /locations/search?query=...` | `GET /locations?name=...`; no matches returns `[]` instead of 404. |
| `GET /buses/info/stops` | `GET /buses/stops`; same collection format. |
| `GET /buses/schedules` | `GET /buses/schedule`; rename `bus_type` to `route`. Defaults are now `route=all`, `day=current`, `direction=all`. Line IDs are campus-qualified; when `stop` is supplied, time filtering uses arrival at that stop, not departure. |
| `GET /buses/stops/{stop_name}` | `GET /buses/schedule?stop={stop_name}&details=true`; read `dep_info` and `stops_time`, not flat arrival records. Arrival filtering still includes in-transit buses. |
| `GET /libraries/space` | `GET /libraries/spaces`. |
| `GET /libraries/lost_and_found` | `GET /libraries/lost-and-found`. |
| `GET /energy/electricity_usage` | `GET /energy/electricity`. |
| `GET /dining/open` | `GET /dining?schedule=today` (or the intended schedule); read each building's nested `restaurants`, not a flat restaurant list. |
| `GET /libraries/calendars` | `GET /calendars`; the list now combines campus and library calendar metadata. |
| `GET /libraries/calendars/{calendar_id}` | `GET /calendars/library-{calendar_id}`; library IDs are `library-main`, `library-hss`, and `library-nanda`. |
| `GET /libraries/calendars/{calendar_id}/events` | `GET /calendars/library-{calendar_id}/events`; same event query parameters. |
| `GET /libraries/calendars/{calendar_id}/events/{event_id}` | `GET /calendars/library-{calendar_id}/events/{event_id}`. |

The earlier removed `/dining/open` and all four `/libraries/calendars` operations
have no compatibility aliases or custom redirects. There is no `/directory/search`
endpoint; use the collection's `query` parameter.

## Course fields and queries

Courses use the publisher's normalized 33-field model. Old field names are not
aliases. REST GET filters and POST matchers now use native numeric/boolean types.
See [course queries](api-guide.md#course-queries) for semester selection, nested
array matching, null semantics and the POST query grammar.

| Before 3.0 | 3.0 field | Type |
| --- | --- | --- |
| `credit` | `credits` | nonnegative number or null |
| `size_limit` | `capacity`, `capacity_unlimited` | nonnegative integer or null; boolean or null |
| `freshman_reservation` | `reserved_for_freshmen` | nonnegative integer or null |
| `suspend` | `is_cancelled` | boolean or null |
| `language` | `language_code` | `"zh"`, `"en"` or null |
| `teacher` | `lecturers` | array of `{label}` or `{name_zh, name_en}` |
| `class_room_and_time` | `meetings` | array of `{classroom, time, time_codes}` |
| `expertise` | `expertises` | array of `{name, type}` |
| `program` | `programs` | string array |
| `required_optional_note` | `curriculum_requirements` | array of `{target, requirement}` |
| `prerequisite` | `prerequisite_text` | string |

Retained names are `id`, `chinese_title`, `english_title`, `note`, `limit_note`,
`object`, `ge_type`, and `no_extra_selection`. The publisher semantics are:
`object` is the course audience/enrollment restriction, `ge_type` is the
general-education audience, and the new `ge_category` is its category.

Other added metadata and unknown-value handling are documented under
[normalized course fields](api-guide.md#normalized-fields-and-30-migration).
Do not guess Chinese/English teacher names from historical `{label}` objects,
or treat unknown numeric/boolean values as zero/false.

## Newsletter matching

REST newsletter fuzzy matching now uses a threshold of 60 instead of 80 for both
source names and article titles, so more names and titles may match. Source-name
matching shares its logic with MCP `get_newsletters`. Exact name and literal title
matching with `fuzzy=false` are unchanged.

MCP no longer truncates matching sources to 15; all are returned in publisher
order, while the three-article preview remains unchanged. The response fields
and tool arguments are unchanged. See [newsletter queries](api-guide.md#newsletter-queries)
for the current REST and MCP response rules.

## MCP client migration

MCP `search_campus` is removed and replaced by independent `search_directory`
and `search_locations` tools, without a compatibility alias. Refresh the client
tool list when upgrading; the current names and titles are listed in the
[API guide](api-guide.md#mcp-tool-names-and-display-titles).

| Tool | Client action |
| --- | --- |
| `search_courses` | Keep `keyword`, `teacher`, `course_id` and `limit`; use optional `semester` to select a semester. The result remains `{count, courses}`, but each course is now the complete normalized model. Old `credit`, `teacher`, `time_and_room` and `language` output fields are removed. |
| `get_bus_schedule` | Use this instead of the earlier removed `get_next_buses` and `get_bus_stops`; no compatibility names are restored. Read the current `buses`, `stop_name` and `stop_info` response fields and the [bus query defaults](api-guide.md#bus-mcp-query). |
| `search_campus` | Replace with `search_directory(query, fuzzy=true)` for contacts and `search_locations(query, fuzzy=true)` for coordinates. Call both tools if both kinds of data are needed. |
| `find_dining` | Always read `buildings[].restaurants`, whether or not `check_open` is supplied. A non-empty `building` filter returns all matching restaurants in every matching building. |
| `get_newsletters` | Handle all matching sources, not a maximum of 15. The per-source three-article preview and response fields are unchanged. |

`search_directory` returns `{departments, people}`, capped at 5 departments and
10 people. `search_locations` returns `{locations}`, capped at 5 locations.
Both filter before limiting, accept required `query` and optional `fuzzy=true`,
and use case-sensitive full-string equality when `fuzzy=false`. Each tool loads
only its own dataset, so an unavailable directory does not prevent location
searches, or vice versa.

REST `/directory` also adds optional `fuzzy=true` with the same matching modes,
while retaining its nested Department array and full-directory behavior for an
omitted or empty query. See [directory queries](api-guide.md#directory-queries)
and [location queries](api-guide.md#location-queries) for current response rules.

**Unreleased 3.0 MCP breaking change:** `find_dining(check_open=...)` no longer
returns `{schedule, open_restaurants}` or applies a global 20-restaurant limit.
Read `buildings[].restaurants` instead (or flatten locally); the requested
schedule remains an input, not a top-level response field. Queries without
`check_open` also return all matches when a non-empty `building` is supplied,
instead of truncating each matching building to 10. Without a non-empty building
filter, the current limit is 10 matching restaurants per building. See
[dining MCP queries](api-guide.md#dining-mcp-query) for the complete response rules.

Course semester failures and live upstream failures are tool errors, not
successful empty results or `{"error": ...}` results. Valid empty results still
succeed. See [availability and readiness](api-guide.md#availability-and-readiness)
for the shared error contract.
