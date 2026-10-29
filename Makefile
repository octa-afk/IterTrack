.PHONY: test dev migrate check simulation demo frontend bootstrap seed-demo reset-demo

SIMULATION_COUNT ?= 3
SIMULATION_INTERVAL ?= 2
SIMULATION_ID ?= 1
# Cada cuánto se renueva el viaje de los camiones que ya terminaron mientras
# corre `make demo`. Sin esto los viajes se completan solos con la telemetría
# (~11 min) y el mapa deja de tener ruta que dibujar: parece que el trazado se
# rompió, cuando en realidad el camión ya no tiene viaje abierto.
DEMO_RENEW_SECONDS ?= 120

# Credenciales locales (ADMIN_API_USER, ADMIN_API_PASSWORD, DATABASE_URL...) que
# viven en el .env raíz. Los targets las cargan en el shell del recetario sin
# pisar lo que ya esté exportado en el entorno.
ENV_FILE ?= .env
LOAD_ENV = set -a; [ -f $(ENV_FILE) ] && . ./$(ENV_FILE) || true; set +a

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
	@$(LOAD_ENV); env/bin/python scripts/simulate_trucks.py \
		--count $(SIMULATION_COUNT) \
		--interval $(SIMULATION_INTERVAL) \
		--id $(SIMULATION_ID)

# Un solo comando para ver la flota moviéndose: migra, bootstrapea, siembra el
# tenant demo, levanta la API si no está arriba, renueva los viajes terminados
# cada DEMO_RENEW_SECONDS y corre el simulador.
# Ctrl+C corta la simulación (y la API, si la levantó este target).
demo:
	@$(LOAD_ENV); set -e; \
	env/bin/alembic upgrade head; \
	env/bin/python -m scripts.bootstrap_platform; \
	env/bin/python -m scripts.seed_demo; \
	api=""; \
	if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then \
		env/bin/uvicorn source.main:app --port 8000 & api=$$!; \
		for i in $$(seq 1 150); do \
			curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break; \
			sleep 0.2; \
		done; \
	else \
		echo "↻ Reutilizando la API que ya responde en :8000"; \
	fi; \
	( while sleep $(DEMO_RENEW_SECONDS); do \
		env/bin/python -m scripts.seed_demo --renew >/dev/null 2>&1 || true; \
	done ) & renew=$$!; \
	trap 'kill $$renew 2>/dev/null || true; [ -n "$$api" ] && kill $$api 2>/dev/null || true' EXIT INT TERM; \
	echo "▶ http://localhost:8000/map — Ctrl+C corta la simulación"; \
	env/bin/python scripts/simulate_trucks.py \
		--count $(SIMULATION_COUNT) \
		--interval $(SIMULATION_INTERVAL) \
		--id $(SIMULATION_ID)

# One-time platform owner and internal organization. Never touched by the demo reset.
bootstrap:
	env/bin/python -m scripts.bootstrap_platform

# Customer-facing demo tenant. Safe to rebuild at any time.
seed-demo:
	env/bin/python -m scripts.seed_demo

reset-demo:
	env/bin/python -m scripts.seed_demo --reset
