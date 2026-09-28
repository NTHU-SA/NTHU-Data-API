# Copilot Instructions

## Development Setup

Before making code changes, ensure you set up the development environment:

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

```sh
# Run tests
uv run --group test pytest tests

# Run tests with coverage
uv run --group test pytest tests --cov=src --cov=tests --cov-report=term-missing
```

## Code Style

This project uses:
- **black** for code formatting
- **isort** for import sorting

Both are configured in `pyproject.toml` and enforced by pre-commit hooks.

## Commit Message Guidelines

We use Conventional Commits for commit messages. Examples include:
- `feat: add new feature`
- `fix: fix a bug` ...