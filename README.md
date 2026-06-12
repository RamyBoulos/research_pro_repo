# Examiner Coach

Examiner Coach is an OSCE feedback training system. It records
spoken examiner feedback, transcribes it, evaluates the feedback against a
structured rubric, and supports bilingual follow-up coaching with evidence
retrieved from a local knowledge base.

## Key Features

- Audio-based OSCE examiner feedback practice with automatic transcription.
- Structured feedback-quality evaluation against six explicit criteria.
- Interactive coaching chat that lets examiners ask follow-up questions,
  request clearer wording, and understand why feedback was scored the way it
  was.
- Evidence-grounded coaching and evaluation using retrieved guidance from a
  local ChromaDB knowledge base.
- Bilingual German/English output for evaluation results, coaching answers,
  criterion labels, suggestions, and certificate-facing UI text.

## What the System Does

The application supports a typical examiner training workflow:

1. A learner watches an OSCE station video.
2. The learner records spoken feedback as if addressing the student.
3. The recording is transcribed through a KISSKI/SAIA speech endpoint.
4. The transcript is evaluated against explicit feedback-quality criteria.
5. Relevant educational guidance is retrieved from a ChromaDB knowledge base.
6. The LLM returns a structured evaluation with scores, suggestions, and a key
   improvement point.
7. The learner can switch between German and English result views without
   regenerating the evaluation.
8. The learner can use the coaching chat to ask follow-up questions, request
   stronger feedback formulations, and receive evidence-grounded explanations
   based on the transcript and evaluation.

## Backend

The backend is organized as a modular AI service:

```text
backend/src/examiner_coach/
├── main.py                  # FastAPI app factory and route registration
├── config.py                # Environment settings, model names, and storage paths
├── api/                     # Pydantic schemas and HTTP route handlers
├── services/                # Transcription, RAG, prompting, coaching, ingestion
├── db/                      # ChromaDB vector-store access
└── utils/                   # Audio and language-resolution helpers
```

The most important backend modules are:

- `services/rag_pipeline.py`: transcript normalization, retrieval, reranking,
  prompt execution, JSON parsing, and final evaluation assembly.
- `services/evaluation_prompt.py`: feedback-quality rubric, scoring anchors,
  prompt contract, and score aggregation helpers.
- `services/coaching_prompt.py`: structured coaching prompt construction for
  multi-turn, bilingual follow-up support.
- `services/document_manager.py`: knowledge-base ingestion, chunking,
  embedding, and indexing.
- `db/vector_store.py`: ChromaDB collection access, queries, upserts, deletes,
  and reset support.

For a fuller backend walkthrough, see [docs/architecture.md](docs/architecture.md).

## Evaluation Criteria

The evaluation rubric currently scores six dimensions of examiner feedback:

- Specific observed behavior named
- Contextual feedback
- Objective and non-evaluative tone
- Explicitly mentioned strength
- Changeable area for improvement
- Concrete improvement plan or next step

Each criterion is scored as a percentage. The backend computes the overall
score and counts criteria as met using the configured threshold.

## Main Request Flow

```text
Frontend audio recording
  -> Next.js submission API
  -> FastAPI /api/transcribe
  -> KISSKI/SAIA transcription endpoint
  -> FastAPI /api/evaluate/full
  -> ChromaDB retrieval
  -> LLM evaluation
  -> structured bilingual backend response
  -> frontend result display
```

The coaching chat uses a similar evidence-grounded backend path:

```text
Frontend coaching question
  -> FastAPI /api/coach
  -> evidence retrieval
  -> bilingual coaching prompt
  -> structured coaching response with updated session summary
```

The backend keeps canonical evaluation and coaching content bilingual where
needed, then resolves the requested display language for the frontend.

## Current RAG Defaults

The production RAG configuration follows the strongest variant observed in the
debug comparison and LLM-as-a-judge workflow: `hyde_k8`.

Current evaluation and coaching retrieval defaults:

```text
retrieval_mode: hyde
candidate_pool_size: 20
final_k: 8
hyde_max_tokens: 300
normalize_to_english: true
criterion_aware_query: true
enable_quality_reranking: true
```

In HyDE mode, the candidate pool is split between direct transcript-based
retrieval and retrieval from a generated hypothetical guidance passage. With
`candidate_pool_size=20`, this means 10 direct candidates and 10 HyDE
candidates are retrieved, deduplicated, reranked, filtered, and reduced to the
final 8 evidence chunks.

Transcription does not use RAG. It uses the configured voice model
(`whisper-large-v2`) and passes the transcript into the later evaluation or
coaching pipeline.

## Repository Layout

```text
backend/                  # FastAPI backend, services, scripts, and tests
frontend/                 # Next.js training interface
knowledge_base/           # Registry and processed ChromaDB vector store
docs/                     # Project documentation
Audiofiles_MockupFeedback # Sample/mock feedback recordings
pyproject.toml            # Python dependencies and tooling config
Makefile                  # Common backend commands
uv.lock                   # Locked Python dependencies
```

Generated caches, legacy frontend copies, and notebook experiments are not part of the main runtime path.

## Requirements

- Python 3.13
- `uv` for Python dependency management
- Node.js and npm for the frontend
- Access to the configured KISSKI/SAIA services
- A populated `.env` file based on `.env.example`
- A frontend `.env.local` file based on `frontend/.env.local.example`

Important backend environment variables:

```env
KISSKI_API_KEY=...
KISSKI_BASE_URL=https://chat-ai.academiccloud.de/v1
KISSKI_VOICE_BASE_URL=https://saia.gwdg.de/v1
KISSKI_LLM_MODEL=meta-llama-3.1-8b-instruct
KISSKI_JUDGE_MODEL=gpt-oss-120b
KISSKI_EMBEDDING_MODEL=multilingual-e5-large-instruct
KISSKI_VOICE_MODEL=whisper-large-v2
KNOWLEDGE_BASE_DIR=knowledge_base/raw
VECTOR_DB_DIR=knowledge_base/processed
REGISTRY_PATH=knowledge_base/registry.json
APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=
```

For production, set `APP_ENV=production` and configure `CORS_ORIGINS` as a
comma-separated list of deployed frontend origins.

## Local Development

Install Python dependencies:

```bash
make sync
```

Start the FastAPI backend in one terminal:

```bash
make dev
```

This runs:

```text
PYTHONPATH=backend/src .venv/bin/uvicorn examiner_coach.main:app --reload --port 8000
```

In development, FastAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

Start the frontend in a second terminal:

```bash
make frontend-dev
```

This is equivalent to:

```bash
cd frontend
npm run dev
```

If you are already inside the `frontend/` directory, either command works:

```bash
make frontend-dev
npm run dev
```

Open the application at:

```text
http://localhost:3000
```

Use the local access code:

```text
OSCE2026SS
```

## Backend Setup

The backend can be started directly with `make dev` or `make backend-dev`.
Both use the local virtual environment and expose the FastAPI service on port
`8000`.

## Knowledge Base

The RAG pipeline retrieves educational evidence from ChromaDB. Source documents are expected under:

```text
knowledge_base/raw/
```

Supported ingestion formats include PDF, DOCX, DOC, and TXT.

Index documents:

```bash
make ingest
```

Reset the vector store before re-indexing:

```bash
make reset-vectors
```

The ingestion pipeline parses documents, cleans parser artifacts, splits text
by document structure, embeds chunks, stores them in ChromaDB, and updates the knowledge-base registry.

## Frontend Setup

The frontend is located in `frontend/`. It provides the training interface,
language switcher, bilingual result display, coaching chat, questionnaire flow,
certificate download, and processing proxies to the FastAPI backend.

```bash
cd frontend
npm install
npm run dev
```

From the repository root, the same frontend dev server can be started with:

```bash
make frontend-dev
```

Set `FASTAPI_BASE_URL` in the frontend environment when the backend is not
running on the default local address:

```env
FASTAPI_BASE_URL=http://127.0.0.1:8000
```

Useful frontend verification commands:

```bash
cd frontend
npm run typecheck
npm run build
```

Further frontend-specific notes are available in
[frontend/README.md](frontend/README.md).

## Development Commands

From the repository root:

```bash
make dev                   # Start the FastAPI backend on port 8000
make backend-dev           # Same as make dev
make frontend-dev          # Start the Next.js frontend
make sync                  # Install/sync Python dependencies
make test                  # Run backend tests
make lint                  # Run Ruff on backend source
make ingest                # Ingest knowledge-base documents
make reset-vectors         # Clear the ChromaDB vector store

# RAG comparison targets create compare_*.json experiment outputs.
make compare-rag           # Generic comparison target with overridable options
make compare-rag-core      # Smaller/faster comparison benchmark
make compare-rag-extended  # Broader comparison benchmark

# RAG judge targets read compare_*.json outputs and create judged_*.json files.
make judge-rag COMPARE=debug/rag_eval_results/compare_....json
make judge-rag-latest      # Judge the newest saved comparison output
```

## RAG Comparison and Judge Workflow

The repository includes tracked benchmark and evaluation scripts for comparing
RAG configurations and then judging the generated outputs with a separate judge
model:

- `backend/data/rag_eval_benchmark.json`: fixed benchmark transcripts and gold
  expectation bands.
- `backend/scripts/compare_rag_variants.py`: runs the benchmark across multiple
  retrieval configurations and writes a comparison JSON file.
- `backend/scripts/judge_rag_outputs.py`: reads a comparison JSON file and asks
  the configured judge model to score each generated evaluation.

The Makefile intentionally separates this into two stages:

1. **Comparison targets** (`make compare-rag*`) generate `compare_*.json`
   files by running benchmark transcripts through different retrieval
   configurations.
2. **Judge targets** (`make judge-rag*`) read a saved `compare_*.json` file
   and generate a `judged_*.json` file with judge-model scores.

Generated comparison and judge outputs are written under
`debug/rag_eval_results/` by default. That directory is intentionally ignored so
large or repeated experiment outputs are not committed; the responsible scripts
and benchmark data are tracked.

Run the smaller comparison set:

```bash
make compare-rag-core
```

This compares no-RAG, direct RAG, unfiltered direct RAG, HyDE, and unfiltered
HyDE variants.

The comparison outputs used during development indicated that `hyde_k8` was the
best overall production candidate. In the illustrative comparison notebook, it
had the lowest average distance to the gold score band and the highest number of
in-band cases among the core variants. The LLM-as-a-judge validation supported
the same overall direction, so the runtime RAG defaults now use `hyde_k8`.

Run the broader comparison set:

```bash
make compare-rag-extended
```

This includes the core variants plus additional `k=4`, `k=12`, and
no-translation retrieval variants.

Run a custom comparison:

```bash
make compare-rag VARIANT_SET=extended \
  RAG_BENCHMARK=backend/data/rag_eval_benchmark.json \
  RAG_OUTPUT=debug/rag_eval_results/compare_custom.json
```

The same options are exposed as Makefile variables:

- `VARIANT_SET`: `core` or `extended`; defaults to `core`.
- `RAG_BENCHMARK`: benchmark JSON path; defaults to
  `backend/data/rag_eval_benchmark.json`.
- `RAG_OUTPUT`: optional explicit comparison output path.

Judge a specific comparison output:

```bash
make judge-rag COMPARE=debug/rag_eval_results/compare_custom.json
```

Judge the newest comparison output:

```bash
make judge-rag-latest
```

The judge target resumes by default with `--resume`. Pass additional judge
options through `JUDGE_ARGS`, for example:

```bash
make judge-rag COMPARE=debug/rag_eval_results/compare_custom.json \
  JUDGE_ARGS="--resume --rate-limit-sleep 60"
```

Judge-related Makefile variables:

- `COMPARE`: required for `make judge-rag`; path to a saved `compare_*.json`.
- `JUDGE_OUTPUT`: optional explicit judged output path.
- `JUDGE_ARGS`: extra flags for the judge script; defaults to `--resume`.

## Tests

Run backend tests with:

```bash
make test
```

The current tests cover selected service-level behavior, including document
processing, transcription, and retrieval configuration. External AI calls should be tested with mocks or controlled sample data where possible.

## API Summary

Active backend endpoints:

- `GET /api/health`: service health check.
- `POST /api/transcribe`: accepts an audio file and returns transcript plus
  duration.
- `POST /api/evaluate`: evaluates a transcript using the RAG pipeline.
- `POST /api/coach`: provides bilingual follow-up coaching based on transcript,
  evaluation, conversation history, retrieved evidence, and the requested
  output language.

## Current Boundaries

- The frontend stores sessions, submissions, and uploaded audio locally.
- Uploaded audio is retained locally only until successful processing; failed
  submissions keep the audio file so the request can be retried or inspected.
- Knowledge-base management is script-driven rather than exposed through the
  active HTTP API.
- The backend depends on external KISSKI/SAIA services for transcription,
  embeddings, document conversion, and LLM responses.
- RAG quality depends on the quality of the indexed source documents and
  chunk metadata.

## Documentation

- [docs/architecture.md](docs/architecture.md): backend-focused architecture
  overview.
- [docs/data_privacy.md](docs/data_privacy.md): data privacy notes.
- [docs/fpq_instrument.md](docs/fpq_instrument.md): feedback questionnaire or
  instrument notes.
- [frontend/README.md](frontend/README.md): frontend setup and deployment notes.
