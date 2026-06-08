.PHONY: dev backend-dev frontend-dev sync test lint ingest reset-vectors compare-rag compare-rag-core compare-rag-extended judge-rag judge-rag-latest

PYTHON := .venv/bin/python
BACKEND_PYTHONPATH := backend/src
RAG_BENCHMARK ?= backend/data/rag_eval_benchmark.json
VARIANT_SET ?= core
RAG_OUTPUT ?=
COMPARE ?=
JUDGE_OUTPUT ?=
JUDGE_ARGS ?= --resume

dev: backend-dev

backend-dev:
	PYTHONPATH=$(BACKEND_PYTHONPATH) .venv/bin/uvicorn examiner_coach.main:app --reload --port 8000

frontend-dev:
	npm --prefix frontend run dev

sync:
	uv sync

test:
	PYTHONPATH=$(BACKEND_PYTHONPATH) .venv/bin/pytest

lint:
	PYTHONPATH=$(BACKEND_PYTHONPATH) .venv/bin/ruff check backend/src

ingest:
	PYTHONPATH=$(BACKEND_PYTHONPATH) $(PYTHON) backend/scripts/ingest_documents.py

reset-vectors:
	PYTHONPATH=$(BACKEND_PYTHONPATH) $(PYTHON) backend/scripts/reset_vector_store.py

# ---------------------------------------------------------------------------
# RAG comparison targets: generate comparison output files.
# These run the evaluator across benchmark transcripts with different retrieval
# settings. They do not judge which variant is best; they only create
# compare_*.json files, usually under ignored debug/rag_eval_results/.
# ---------------------------------------------------------------------------

# Generic comparison target.
# Use this when you need custom options:
#   make compare-rag VARIANT_SET=extended
#   make compare-rag RAG_BENCHMARK=backend/data/other.json
#   make compare-rag RAG_OUTPUT=debug/rag_eval_results/compare_custom.json
compare-rag:
	PYTHONPATH=$(BACKEND_PYTHONPATH) $(PYTHON) backend/scripts/compare_rag_variants.py --benchmark $(RAG_BENCHMARK) --variant-set $(VARIANT_SET) $(if $(RAG_OUTPUT),--output $(RAG_OUTPUT),)

# Shortcut for the smaller, faster comparison set:
# no RAG, direct RAG, unfiltered direct RAG, HyDE, and unfiltered HyDE.
compare-rag-core:
	$(MAKE) compare-rag VARIANT_SET=core

# Shortcut for the broader comparison set:
# all core variants plus k=4/k=12 and no-translation variants.
compare-rag-extended:
	$(MAKE) compare-rag VARIANT_SET=extended

# ---------------------------------------------------------------------------
# RAG judge targets: score saved comparison output files.
# Run one of these after a compare-rag* target. These read compare_*.json files
# and write judged_*.json files using the configured judge model.
# ---------------------------------------------------------------------------

# Generic judge target for a specific comparison file.
# Required:
#   make judge-rag COMPARE=debug/rag_eval_results/compare_YYYYMMDDTHHMMSSZ.json
# Optional:
#   make judge-rag COMPARE=... JUDGE_OUTPUT=debug/rag_eval_results/judged_custom.json
#   make judge-rag COMPARE=... JUDGE_ARGS="--resume --rate-limit-sleep 60"
judge-rag:
	@if [ -z "$(COMPARE)" ]; then \
		echo "Set COMPARE=debug/rag_eval_results/compare_....json"; \
		exit 2; \
	fi
	PYTHONPATH=$(BACKEND_PYTHONPATH) $(PYTHON) backend/scripts/judge_rag_outputs.py $(COMPARE) $(if $(JUDGE_OUTPUT),--output $(JUDGE_OUTPUT),) $(JUDGE_ARGS)

# Convenience judge target for the most recent compare_*.json file.
# Typical flow:
#   make compare-rag-core
#   make judge-rag-latest
judge-rag-latest:
	@latest=$$(ls -t debug/rag_eval_results/compare_*.json 2>/dev/null | head -n 1); \
	if [ -z "$$latest" ]; then \
		echo "No comparison outputs found. Run make compare-rag-core or make compare-rag-extended first."; \
		exit 2; \
	fi; \
	$(MAKE) judge-rag COMPARE=$$latest JUDGE_ARGS="$(JUDGE_ARGS)" $(if $(JUDGE_OUTPUT),JUDGE_OUTPUT=$(JUDGE_OUTPUT),)
