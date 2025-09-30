# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.11-slim
FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHERUSAGESTATS=false \
    PATH="/app/.venv/bin:${PATH}" \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl tini ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --yes && mv /root/.local/bin/uv /usr/local/bin/ && uv --version

# Copy dependency manifest and resolve env first for layer caching
COPY pyproject.toml ./
RUN uv sync --no-dev --frozen || uv sync --no-dev

# Copy application source (after deps for cache efficiency)
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
