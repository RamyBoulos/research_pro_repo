.PHONY: dev sync test lint

dev:
	PYTHONPATH=backend/src uv run uvicorn examiner_coach.main:app --reload

sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check backend/src
	
ingest:
	PYTHONPATH=backend/src uv run python backend/scripts/ingest_documents.py