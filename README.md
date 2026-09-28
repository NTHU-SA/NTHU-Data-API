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
## Credit
This project is maintained by NTHUSA 32nd.

## License
This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).

## Acknowledgements
Thanks to SonarCloud for providing code quality metrics:

[![SonarCloud](https://sonarcloud.io/images/project_badges/sonarcloud-white.svg)](https://sonarcloud.io/summary/new_code?id=NTHU-SA_NTHU-Data-API)