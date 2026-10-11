.PHONY: install dev api web emulator test test-emulator lint check

install:
	uv sync
	cd frontend && npm ci

api:
	uv run cp serve

web:
	cd frontend && npm run dev

emulator:
	docker compose up -d firestore

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	cd frontend && npm run typecheck

test:
	uv run pytest -q

test-emulator: emulator
	FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 uv run pytest -q

check: lint test
	cd frontend && npm run build
