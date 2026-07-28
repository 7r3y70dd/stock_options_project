#!/usr/bin/env bash
set -euo pipefail

echo "[cognimoss] starting validation for stock_options_project"

# Do not source .env files here.
# This script should use safe test-only values.

export ENVIRONMENT=test
export TESTING=true

export TEST_DB_CONTAINER="${TEST_DB_CONTAINER:-cognimoss-options-test-postgres}"
export TEST_REDIS_CONTAINER="${TEST_REDIS_CONTAINER:-cognimoss-options-test-redis}"

export POSTGRES_USER="${POSTGRES_USER:-options_user}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-options_password}"
export POSTGRES_DB="${POSTGRES_DB:-options_tracker_test}"

export DATABASE_URL="${DATABASE_URL:-postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5433/${POSTGRES_DB}}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6380/0}"

cleanup() {
  docker rm -f "$TEST_DB_CONTAINER" "$TEST_REDIS_CONTAINER" >/dev/null 2>&1 || true
}

trap cleanup EXIT

echo "[cognimoss] cleaning old test containers"
cleanup

echo "[cognimoss] starting postgres"
docker run -d \
  --name "$TEST_DB_CONTAINER" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -p 127.0.0.1:5433:5432 \
  postgres:15-alpine >/dev/null

echo "[cognimoss] starting redis"
docker run -d \
  --name "$TEST_REDIS_CONTAINER" \
  -p 127.0.0.1:6380:6379 \
  redis:7-alpine >/dev/null

echo "[cognimoss] waiting for postgres"
for i in $(seq 1 30); do
  if docker exec "$TEST_DB_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi

  if [ "$i" = "30" ]; then
    echo "[cognimoss] ERROR: postgres did not become ready"
    docker logs "$TEST_DB_CONTAINER" || true
    exit 1
  fi

  sleep 1
done

echo "[cognimoss] preparing python test environment"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" -m venv .venv
. .venv/bin/activate

python -m pip install -U pip setuptools wheel

if [ -f requirements.txt ]; then
  python -m pip install -r requirements.txt
fi

python -m pip install pytest

echo "[cognimoss] running pytest"
python -m pytest -q -ra --continue-on-collection-errors
