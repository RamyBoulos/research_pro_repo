.PHONY: dev sync test lint ingest reset-vectors

dev:
	PYTHONPATH=backend/src uvicorn examiner_coach.main:app --reload

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
