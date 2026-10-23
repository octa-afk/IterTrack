.PHONY: test dev migrate check simulation frontend bootstrap seed-demo reset-demo

SIMULATION_COUNT ?= 3
SIMULATION_INTERVAL ?= 2
SIMULATION_ID ?= 1
SIMULATION_PLATE ?= ABC123

test:
	env/bin/python -m pytest tests/ -v

# Builds the React app that FastAPI serves. Run it before `make test` when you
# want the SPA-serving tests to run instead of being skipped.
frontend:
	cd frontend && npm ci && npm run build

dev:
	env/bin/uvicorn source.main:app --reload --port 8000

migrate:
	env/bin/alembic upgrade head

check:
	env/bin/python -m ruff check source scripts tests
	env/bin/mypy source scripts tests

simulation:
	env/bin/python scripts/simulate_trucks.py \
		--count $(SIMULATION_COUNT) \
		--interval $(SIMULATION_INTERVAL) \
		--id $(SIMULATION_ID) \
		--plate $(SIMULATION_PLATE)

# One-time platform owner and internal organization. Never touched by the demo reset.
bootstrap:
	env/bin/python -m scripts.bootstrap_platform

# Customer-facing demo tenant. Safe to rebuild at any time.
seed-demo:
	env/bin/python -m scripts.seed_demo

reset-demo:
	env/bin/python -m scripts.seed_demo --reset
