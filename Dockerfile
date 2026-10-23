# syntax=docker/dockerfile:1

# ---- Stage 1: build the React SPA that FastAPI serves ----
FROM node:22-alpine AS frontend

WORKDIR /build/frontend
# Copy manifests first so the dependency layer is cached across source changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# psycopg2-binary ships its own libpq, so no build toolchain is needed here.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY source/ ./source/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY pyproject.toml ./
# The repository ignores alembic.ini because a local one may hold credentials.
# env.py overrides sqlalchemy.url from the environment, so the example is safe.
COPY alembic.ini.example ./alembic.ini
COPY --from=frontend /build/frontend/dist ./frontend/dist

RUN useradd --create-home --uid 1001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT','8000') + '/health', timeout=3)"]

# The entrypoint migrates, optionally bootstraps and seeds, then execs the
# command it receives. Pass a command to run the simulator worker instead.
ENTRYPOINT ["/app/scripts/docker_entrypoint.sh"]
