#!/bin/sh
# Container entrypoint: prepare the database, then run the given command.
#
# Every step is idempotent, so restarting the container is safe.
#
#   RUN_MIGRATIONS       run `alembic upgrade head` (default: true)
#   BOOTSTRAP_PLATFORM   create the internal organization and platform owner
#   SEED_DEMO_ON_BOOT    create the demo tenant if it is missing (never resets)
#
# A worker container should set RUN_MIGRATIONS=false and pass its own command,
# so two processes never race on the same migration.
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "→ alembic upgrade head"
  alembic upgrade head
fi

if [ "${BOOTSTRAP_PLATFORM:-false}" = "true" ]; then
  echo "→ bootstrap de plataforma"
  python -m scripts.bootstrap_platform
fi

if [ "${SEED_DEMO_ON_BOOT:-false}" = "true" ]; then
  echo "→ seed de demo"
  python -m scripts.seed_demo
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# Caddy es lo único que alcanza este puerto, así que se confía en su
# X-Forwarded-For: sin esto todos los clientes comparten la IP del proxy y el
# límite de intentos bloquearía a todo el mundo junto.
exec uvicorn source.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips='*'
