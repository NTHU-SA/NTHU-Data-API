# Development guide

[Back to README](../README.md) | [API guide](api-guide.md) | [Release guide](releasing.md)

Use the [README quick start](../README.md#run-locally) to install Python 3.14+
dependencies with uv and launch the service. This guide covers configuration,
local validation and diagnosing external data checks. Consumer-facing behavior
belongs in the API guide; version preparation and deployment belong in the
release guide.

## Contents

- [Configuration](#configuration)
- [Formatting and offline tests](#formatting-and-offline-tests)
- [REST and MCP contract baselines](#rest-and-mcp-contract-baselines)
- [Published data and deployment checks](#published-data-and-deployment-checks)

## Configuration

Settings load environment variables and `.env`. Start from [`.env.template`](../.env.template):

| Variable | Template value | Purpose |
| --- | --- | --- |
| `DEV_MODE` | `True` | Enable development mode with automatic reload |
| `PORT` | `5000` | HTTP server port |
| `NTHU_DATA_URL` | `https://data.nthusa.tw` | Published dataset source |
| `FILE_DETAILS_CACHE_EXPIRY` | `300` | Dataset freshness-check TTL in seconds; must be positive |
| `DATA_HTTP_TIMEOUT` | `15` | Dataset HTTP timeout in seconds; must be positive |

Without an override, `DEV_MODE` defaults to `False`. Additional server and CORS
settings are defined in [`settings.py`](../src/data_api/core/settings.py).

`GET /` provides service discovery; `GET /ping` and `HEAD /ping` report cached
dataset readiness, not liveness. Do not use `/ping` as a startup or liveness probe.
See [availability and readiness](api-guide.md#availability-and-readiness)
for status codes and limitations.

## Formatting and offline tests

Run commands from the repository root after `uv sync --all-groups`.
Black and isort use the configuration in `pyproject.toml`.

```sh
uv run pre-commit install
uv run pre-commit run --all-files
uv run --group test pytest tests
```

Use the smallest relevant test selection while iterating, for example:

```sh
uv run --group test pytest tests/test_data_manager.py tests/test_runtime_lifecycle.py
```

Run the full suite for shared services, lifecycle or public-contract changes.
To match the CI coverage reports and 85% threshold:

```sh
uv run --group test pytest -n auto tests --cov=src --cov=tests --cov-report=xml --cov-report=html:coverage --cov-fail-under=85
```

The default suite uses mock transports and injected clocks and blocks real HTTPX
traffic. Preserve that isolation in new tests; run external checks separately.
Architecture, runtime ownership and CI maintenance constraints are documented in
[Copilot instructions](../.github/copilot-instructions.md).

## REST and MCP contract baselines

The offline suite compares structured OpenAPI and MCP baselines. Check them directly with:

```sh
uv run --locked python -m data_api.checks.openapi
uv run --locked python -m data_api.checks.mcp
```

For an intentional, reviewed API change, regenerate the affected baselines and
inspect the fixture diffs:

```sh
uv run --locked python -m data_api.checks.openapi --write
uv run --locked python -m data_api.checks.mcp --write
```

Do not regenerate to hide unexpected removed routes/tools/parameters or changed
operation IDs, defaults, schemas or headers. Documentation-only wording is ignored.
Review REST and MCP together, update the [API guide](api-guide.md), and follow the
[release compatibility policy](releasing.md#version-source-and-compatibility).

## Published data and deployment checks

[External Data Contracts](../.github/workflows/published_contracts.yml) is a separate
workflow, scheduled daily at 00:00 UTC and runnable from Actions with mode
`published`, `smoke`, or `all`. These jobs report external publication/deployment
failures separately from the ordinary **Test** workflow.

Run the same checks locally with the locked runtime dependencies. Unlike the
offline suite, these commands access the supplied live service:

```sh
uv run --locked python -m data_api.checks.published --data-url https://data.nthusa.tw
uv run --locked python -m data_api.checks.smoke --api-url https://api.nthusa.tw
```

### Publisher validation

The publisher check requires every configured dataset in the manifest, checks
HTTP status, JSON content type, JSON structure and optional SHA-256, and validates
complete candidates and course/bus transformations. It then exercises local REST
serialization using only those downloaded bytes, with no live-integration calls.
Missing checksums and versions remain compatible with legacy manifests.
All four RSS feeds must be present; each may contain zero articles. No historical
record count is required.

### Deployed API smoke check

The smoke check reads `/ping` and representative snapshot GETs, including all four
RSS feeds, and verifies response schemas and timing/count headers. After deployment,
dispatch mode `smoke` with the deployment's `api_url`; it is not a liveness probe
or a guarantee about on-demand library/electricity services or every instance.

### Diagnosing failures

Failures print the dataset/endpoint, `stage` and safe `reason`, then exit nonzero:

| Stage | Meaning |
| --- | --- |
| `http`, `content-type`, `json` | Delivery failure |
| `checksum` | Manifest/data inconsistency |
| `candidate`, `transformation`, `serialization` | Contract drift |
| `readiness`, `response-schema`, `headers` | Deployment defect |

Fix the indicated publisher or deployment problem and rerun the matching command,
or use **Re-run failed jobs** in Actions. There are no automatic HTTP retries.
