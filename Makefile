.PHONY: dev backend-dev frontend-dev sync test lint ingest reset-vectors

dev: backend-dev

backend-dev:
	PYTHONPATH=backend/src .venv/bin/uvicorn examiner_coach.main:app --reload --port 8000

frontend-dev:
	npm --prefix frontend run dev

sync:
	uv sync

test:
	PYTHONPATH=backend/src pytest

lint:
	PYTHONPATH=backend/src ruff check backend/src

ingest:
	PYTHONPATH=backend/src python backend/scripts/ingest_documents.py

reset-vectors:
	PYTHONPATH=backend/src python backend/scripts/reset_vector_store.py
