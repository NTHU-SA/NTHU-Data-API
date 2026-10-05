# NTHU-Data-API

Public campus data for National Tsing Hua University developers, available through
a REST API and MCP tools.

[![Tests](https://github.com/NTHU-SA/NTHU-Data-API/actions/workflows/tests.yml/badge.svg)](https://github.com/NTHU-SA/NTHU-Data-API/actions/workflows/tests.yml)
[![Test Coverage](https://coverage-badge.samuelcolvin.workers.dev/NTHU-SA/NTHU-Data-API.svg)](https://coverage-badge.samuelcolvin.workers.dev/redirect/NTHU-SA/NTHU-Data-API)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Use the API

| Resource | URL |
| --- | --- |
| REST API | https://api.nthusa.tw |
| Interactive documentation | https://api.nthusa.tw/docs |
| OpenAPI schema | https://api.nthusa.tw/openapi.json |
| MCP endpoint | https://api.nthusa.tw/mcp |

### Available data

| Data | Main endpoints |
| --- | --- |
| Courses | `GET /courses`, `POST /courses/query` |
| Campus directory | `GET /directory` |
| Announcements | `GET /announcements`, `GET /announcements/sources` |
| Newsletters | `GET /newsletters`, `GET /newsletters/sources` |
| Locations | `GET /locations` |
| Campus buses | `GET /buses/routes`, `GET /buses/stops`, `GET /buses/schedule` |
| Dining | `GET /dining` |
| Campus and library calendars | `GET /calendars`, `GET /calendars/{calendar_id}/events` |
| Library services | `GET /libraries/spaces`, `GET /libraries/lost-and-found` |
| Live electricity usage | `GET /energy/electricity` |

For example, retrieve the next buses serving a stop:

```sh
curl "https://api.nthusa.tw/buses/schedule?stop=台積館&limit=5"
```

See the [API guide](docs/api-guide.md) for query examples, MCP tool names,
response conventions, readiness checks, and migration notes for deprecated endpoints.
Use Swagger UI for complete parameter and response schemas.

## Run locally

Requires **Python 3.14+** and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
git clone https://github.com/NTHU-SA/NTHU-Data-API.git
cd NTHU-Data-API
uv sync --all-groups
```

Copy `.env.template` to `.env` and adjust it as needed:

```sh
cp .env.template .env
```

On PowerShell, use `Copy-Item .env.template .env` instead.

```sh
uv run python main.py
```

The local API is available at `http://localhost:5000`, with documentation at
`http://localhost:5000/docs` and MCP at `http://localhost:5000/mcp`.

### Configuration

| Variable | Template value | Purpose |
| --- | --- | --- |
| `DEV_MODE` | `True` | Enable development mode with automatic reload |
| `PORT` | `5000` | HTTP server port |
| `NTHU_DATA_URL` | `https://data.nthusa.tw` | Published dataset source |
| `FILE_DETAILS_CACHE_EXPIRY` | `300` | Dataset freshness-check TTL in seconds; must be positive |
| `DATA_HTTP_TIMEOUT` | `15` | Dataset HTTP timeout in seconds; must be positive |

Without an override, `DEV_MODE` defaults to `False`. Additional server and CORS
settings are defined in [`settings.py`](src/data_api/core/settings.py).

`GET /` provides service discovery; `GET /ping` and `HEAD /ping` report cached
dataset readiness, not liveness. Do not use `/ping` as a startup or liveness probe.
See [availability and readiness](docs/api-guide.md#availability-and-readiness)
for status codes and limitations.

## Contributing

Install formatting hooks and run tests before submitting changes:

```sh
uv run pre-commit install
uv run --group test pytest tests
```

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/),
such as `feat: add a feature` or `fix: fix a bug`.
Development workflow, architecture, compatibility rules, and CI maintenance
details are in [Copilot instructions](.github/copilot-instructions.md).

## Credits and license

Maintained by NTHUSA 32nd. Licensed under the [MIT License](LICENSE).

Thanks to [SonarCloud](https://sonarcloud.io/summary/new_code?id=NTHU-SA_NTHU-Data-API)
for providing code quality metrics.
