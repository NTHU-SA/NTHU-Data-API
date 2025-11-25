# Copilot Instructions

## Development Setup

Before making code changes, ensure you set up the development environment:

### Installing Dependencies

```sh
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies (includes pre-commit)
pip install -r requirements-dev.txt

# Install test dependencies
pip install -r requirements-tests.txt
```

### Pre-commit Setup

This project uses pre-commit hooks to ensure code quality. Before making commits:

```sh
# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files manually
pre-commit run --all-files
```

## Running Tests

```sh
# Run tests
python -m pytest tests -W ignore::DeprecationWarning

# Run tests with coverage
python -m pytest tests -W ignore::DeprecationWarning --cov=src --cov=tests --cov-report=term-missing
```

## Code Style

This project uses:
- **black** for code formatting
- **isort** for import sorting

Both are configured in `pyproject.toml` and enforced by pre-commit hooks.
