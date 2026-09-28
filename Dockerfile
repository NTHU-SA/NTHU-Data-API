# Stage 1: Build dependencies
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_COMPILE_BYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
# jieba has no wheel; building its hash-locked sdist is required.
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
COPY main.py ./
# Build the local project after installing the locked third-party dependencies.
RUN uv sync --locked --no-dev

# Stage 2: Final image
FROM python:3.14-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Set timezone to Taipei
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/"$TZ" /etc/localtime && \
    echo "$TZ" > /etc/timezone && \
    groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

# Copy the virtual environment and application code
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 5000
CMD ["python", "main.py"]