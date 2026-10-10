.PHONY: test dev migrate check simulation

SIMULATION_COUNT ?= 3
SIMULATION_INTERVAL ?= 2
SIMULATION_ID ?= 1
SIMULATION_PLATE ?= ABC123

test:
	env/bin/python -m pytest tests/ -v

dev:
	env/bin/uvicorn source.main:app --reload --port 8000

migrate:
	env/bin/alembic upgrade head

check:
	env/bin/python -m py_compile source/main.py
	env/bin/python -m py_compile source/services/tracking.py
	env/bin/python -m py_compile source/services/auth.py
	env/bin/python -m py_compile source/models/user.py

simulation:
	env/bin/python scripts/simulate_trucks.py \
		--count $(SIMULATION_COUNT) \
		--interval $(SIMULATION_INTERVAL) \
		--id $(SIMULATION_ID) \
		--plate $(SIMULATION_PLATE)
