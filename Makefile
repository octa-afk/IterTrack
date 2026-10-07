.PHONY: test dev migrate check

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
