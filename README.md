# Examiner Coach

Examiner Coach is an OSCE feedback training system. It records
spoken examiner feedback, transcribes it, evaluates the feedback against a
structured rubric, and supports follow-up coaching with evidence retrieved from a local knowledge base.

## What the System Does

The application supports a typical examiner training workflow:

1. A learner watches an OSCE station video.
2. The learner records spoken feedback as if addressing the student.
3. The recording is transcribed through a KISSKI/SAIA speech endpoint.
4. The transcript is evaluated against explicit feedback-quality criteria.
5. Relevant educational guidance is retrieved from a ChromaDB knowledge base.
6. The LLM returns a structured evaluation with scores, suggestions, and a key
   improvement point.
7. The learner can ask follow-up coaching questions based on the transcript and
   evaluation.

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
  multi-turn follow-up support.
- `services/document_manager.py`: knowledge-base ingestion, chunking,
  embedding, and indexing.
- `db/vector_store.py`: ChromaDB collection access, queries, upserts, deletes,
  and reset support.

For a fuller backend walkthrough, see [docs/architecture.md](docs/architecture.md).

## Evaluation Criteria

The evaluation rubric currently scores six dimensions of examiner feedback:

- Specific observed behavior named
- Timely and contextual feedback
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
  -> FastAPI /api/evaluate
  -> ChromaDB retrieval
  -> LLM evaluation
  -> structured backend response
  -> frontend result display
```

Coaching uses a similar backend path:

```text
Frontend coaching question
  -> FastAPI /api/coach
  -> evidence retrieval
  -> coaching prompt
  -> structured coaching response
```

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

Important backend environment variables:

```env
KISSKI_API_KEY=...
KISSKI_BASE_URL=https://chat-ai.academiccloud.de/v1
KISSKI_VOICE_BASE_URL=https://saia.gwdg.de/v1
KISSKI_LLM_MODEL=llama-3.3-70b-instruct
KISSKI_EMBEDDING_MODEL=multilingual-e5-large-instruct
KISSKI_VOICE_MODEL=whisper-large-v2
KNOWLEDGE_BASE_DIR=knowledge_base/raw
VECTOR_DB_DIR=knowledge_base/processed
REGISTRY_PATH=knowledge_base/registry.json
APP_ENV=development
LOG_LEVEL=INFO
```

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

The frontend is located in `frontend/`. It provides the training interface and proxies processing requests to the FastAPI backend.

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

Further frontend-specific notes are available in
[frontend/README.md](frontend/README.md).

## Development Commands

From the repository root:

```bash
make dev            # Start the FastAPI backend on port 8000
make backend-dev    # Same as make dev
make frontend-dev   # Start the Next.js frontend
make sync           # Install/sync Python dependencies
make test           # Run backend tests
make lint           # Run Ruff on backend source
make ingest         # Ingest knowledge-base documents
make reset-vectors  # Clear the ChromaDB vector store
```

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
- `POST /api/coach`: provides follow-up coaching based on transcript,
  evaluation, conversation history, and retrieved evidence.

## Current Boundaries

- The frontend stores sessions, submissions, and uploaded audio locally.
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
- [frontend/README.md](frontend/README.md): frontend setup and MVP notes.
