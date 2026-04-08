.PHONY: db-up db-down stack-up migrate test test-all vertical-slice install \
	frontend-install frontend-test frontend-build frontend-e2e ci

PYTHON ?= python3.13
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt

db-up:
	docker compose up -d db

db-down:
	docker compose down

# PostGIS + API + nginx Field PWA (http://localhost:8080, API :8090)
stack-up:
	docker compose --profile stack up -d --build

migrate:
	PYTHONPATH=. $(PY) -m alembic upgrade head

test:
	PYTHONPATH=. $(PY) -m pytest tests/ -v -m "not integration"

test-all:
	PYTHONPATH=. $(PY) -m pytest tests/ -v

# Fast local gate: backend unit tests + frontend Vitest (no Playwright, no browser install).
ci: test frontend-test

# Full smoke against a local KMZ path (requires db-up + migrate first).
vertical-slice:
	@test -n "$(FERRY_KMZ)" || (echo "Set FERRY_KMZ=/abs/path/to/FerryCounty_Complete_Roads_v2.kmz" && exit 1)
	PYTHONPATH=. $(PY) scripts/vertical_slice.py "$(FERRY_KMZ)"

frontend-install:
	cd frontend && npm ci

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

frontend-e2e:
	cd frontend && npx playwright install chromium && npm run e2e
