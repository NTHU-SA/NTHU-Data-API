# NTHU-Data-API

為國立清華大學開發者提供公開校園資料，透過 REST API 與 MCP 工具，
讓應用程式與 AI 助理都能查詢校園資訊。

Public campus data for National Tsing Hua University developers, available through
a REST API and MCP tools for applications and AI assistants.

[![Tests](https://github.com/NTHU-SA/NTHU-Data-API/actions/workflows/tests.yml/badge.svg)](https://github.com/NTHU-SA/NTHU-Data-API/actions/workflows/tests.yml)
[![Test Coverage](https://coverage-badge.samuelcolvin.workers.dev/NTHU-SA/NTHU-Data-API.svg)](https://coverage-badge.samuelcolvin.workers.dev/redirect/NTHU-SA/NTHU-Data-API)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 使用入口 / Use the API

| 資源 / Resource | URL |
| --- | --- |
| REST API | https://api.nthusa.tw |
| 互動文件 / Interactive documentation | https://api.nthusa.tw/docs |
| OpenAPI schema | https://api.nthusa.tw/openapi.json |
| MCP endpoint | https://api.nthusa.tw/mcp |

### 校園資料 / Available data

主要資料由 Data Scraper 發布的 JSON 提供；圖書館空間、失物招領與用電資訊則依請求即時查詢。
REST 與 MCP 共用資料服務，課程支援指定學期查詢。

Most data comes from JSON published by Data Scraper; library spaces, lost items,
and electricity usage are fetched on demand. REST and MCP share data services,
including semester-specific course queries.

| 資料 / Data | 主要端點 / Main endpoints |
| --- | --- |
| 課程<br>Courses | `GET /courses`, `GET /courses/semesters`, `GET /courses/{semester}`, `POST /courses/query` |
| 校園通訊錄<br>Campus directory | `GET /directory` |
| 校園公告<br>Announcements | `GET /announcements`, `GET /announcements/sources` |
| 電子報<br>Newsletters | `GET /newsletters`, `GET /newsletters/sources` |
| 校園地點<br>Locations | `GET /locations` |
| 校園公車<br>Campus buses | `GET /buses/routes`, `GET /buses/stops`, `GET /buses/schedule` |
| 餐飲<br>Dining | `GET /dining` |
| 校園與圖書館行事曆<br>Campus and library calendars | `GET /calendars`, `GET /calendars/{calendar_id}/events` |
| 圖書館服務<br>Library services | `GET /libraries/spaces`, `GET /libraries/lost-and-found`, `GET /libraries/rss/{rss_type}` |
| 即時用電<br>Live electricity usage | `GET /energy/electricity` |

例如，查詢行經指定站點的接下來五班公車：

For example, retrieve the next buses serving a stop:

```sh
curl "https://api.nthusa.tw/buses/schedule?stop=台積館&limit=5"
```

查詢範例、MCP 工具與回應規則請見 [API guide](docs/api-guide.md)；
升級既有應用程式請先閱讀 [3.0 遷移說明](docs/migration-3.0.md)。
完整參數與回應結構可於 Swagger UI 查閱。

See the [API guide](docs/api-guide.md) for query examples, MCP tools and response
conventions, and the [3.0 migration guide](docs/migration-3.0.md)
when upgrading clients. Swagger UI provides complete parameter and response schemas.

### 文件導覽 / Documentation

API 使用者請閱讀 API guide；開發、檢查與部署流程分別整理於以下文件。

Start with the API guide to consume the service; development, validation and
deployment procedures live in the focused guides below.

| 文件 / Guide | 內容 / Contents |
| --- | --- |
| [API guide](docs/api-guide.md) | 查詢、MCP、遷移與可用性<br>Queries, MCP, migration and availability |
| [3.0 migration guide](docs/migration-3.0.md) | 舊端點替換與課程欄位遷移<br>Endpoint replacements and course field migration |
| [Development guide](docs/development.md) | 設定、測試與資料契約檢查<br>Configuration, tests and data-contract checks |
| [Release guide](docs/releasing.md) | 版本準備與 Cloud Build 部署<br>Version preparation and Cloud Build deployment |

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

See the [development guide](docs/development.md#configuration) for configuration.

## Contributing

Install formatting hooks and run tests before submitting changes:

```sh
uv run pre-commit install
uv run pre-commit run --all-files
uv run --group test pytest tests
```

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/),
such as `feat: add a feature` or `fix: fix a bug`.
See the [development guide](docs/development.md) for offline coverage, REST/MCP
contract baselines and external checks. Architecture and internal maintenance
constraints are in [Copilot instructions](.github/copilot-instructions.md).
Version preparation and deployment are covered in the [release guide](docs/releasing.md).

## 致謝與授權 / Credits and license

由清華大學第 32 屆學生會維護，採用 [MIT License](LICENSE)。

Maintained by NTHUSA 32nd. Licensed under the [MIT License](LICENSE).

感謝 [SonarCloud](https://sonarcloud.io/summary/new_code?id=NTHU-SA_NTHU-Data-API) 提供程式碼品質指標。

Thanks to [SonarCloud](https://sonarcloud.io/summary/new_code?id=NTHU-SA_NTHU-Data-API)
for providing code quality metrics.

## Changelog

- **3.0.0**：改善 MCP 工具設計與資料維護性，強化資料更新、快取與錯誤處理的穩定度，並精簡整併 API 端點。擴充校園與圖書館行事曆資料，採用標準化課程欄位，支援 REST 與 MCP 指定學期查詢；介面調整請見 [3.0 遷移說明](docs/migration-3.0.md)。

  Improves MCP design, data maintainability and refresh/cache/error handling; consolidates API endpoints, expands campus/library calendars, and adds normalized courses with semester selection in REST and MCP. See the [3.0 migration guide](docs/migration-3.0.md) for interface changes.

- **2.0.0**：新增 MCP 介面，讓 AI 助理也能查詢校園資訊；主要資料改用 Data Scraper 提供的 JSON，將資料爬取與 API 服務分離，提升可維護性。

  Adds MCP for AI assistants and moves most data to Data Scraper JSON, separating scraping from API delivery for easier maintenance.

- **1.0.0**：推出校園資料 REST API，由 API 端即時爬取來源資料並進行處理，提供課程、公車、餐飲與用電等資訊查詢。

  Introduces the campus REST API, with API-side live scraping and processing for courses, buses, dining and electricity information.
