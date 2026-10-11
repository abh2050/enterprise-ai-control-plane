# Stage 1: build the console
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: API and static console
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ backend/
COPY configs/ configs/
RUN uv sync --frozen --no-dev
COPY --from=frontend /app/frontend/dist frontend/dist
RUN useradd --uid 10001 --no-create-home app
USER app
# Cloud Run sets PORT. Containers only run with IAP identity; fixture identity refuses
# to bind to 0.0.0.0 by design.
ENV IDENTITY_MODE=iap BIND_HOST=0.0.0.0
CMD ["sh", "-c", "exec uv run --no-sync cp serve --host 0.0.0.0 --port ${PORT:-8080}"]
