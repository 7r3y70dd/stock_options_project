#!/usr/bin/env bash
set -euo pipefail

echo "[cognimoss] starting validation for stock_options_project"

# Do not source .env files here.
# Cognimoss should pass only safe test env vars.

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

cleanup

docker run -d \
  --name "$TEST_DB_CONTAINER" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -p 127.0.0.1:5433:5432 \
  postgres:15-alpine >/dev/null

docker run -d \
  --name "$TEST_REDIS_CONTAINER" \
  -p 127.0.0.1:6380:6379 \
  redis:7-alpine >/dev/null

echo "[cognimoss] waiting for postgres"

for i in $(seq 1 30); do
  if docker exec "$TEST_DB_CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[cognimoss] running pytest"
python -m pytest -q -ra --continue-on-collection-errors

