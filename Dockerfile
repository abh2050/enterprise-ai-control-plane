# Stage 1: build the console
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: API, console, and batch jobs (one image; Cloud Run jobs override the command)
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 UV_NO_SYNC=1
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ backend/
RUN uv sync --frozen --no-dev
COPY configs/ configs/
COPY data/ data/
COPY artifacts/ artifacts/
COPY docs/ docs/
COPY --from=frontend /app/frontend/dist frontend/dist
RUN useradd --uid 10001 --create-home app && chown -R app /app
USER app
ENV PATH="/app/.venv/bin:$PATH"
# Cloud Run sets PORT. The container always runs with IAP identity; fixture identity
# refuses to bind to 0.0.0.0 by design.
ENV IDENTITY_MODE=iap BIND_HOST=0.0.0.0
CMD ["sh", "-c", "exec cp serve --host 0.0.0.0 --port ${PORT:-8080}"]
