# Examiner Coach Architecture

## Purpose and Scope

Examiner Coach is an AI-assisted OSCE examiner training system. It helps
examiners practice spoken feedback, evaluates that feedback against explicit
quality criteria, and offers follow-up coaching grounded in educational
guidance.

This document focuses on the backend architecture, because the backend is the
main technical scope of the project. The frontend is described only as the
client layer that captures recordings, displays results, and calls the backend
services.

Empty, generated, legacy, or experimental-only files are intentionally excluded
from this overview.

## System Overview

The application is split into three logical layers:

1. **Frontend training interface**
   A Next.js application that manages login, video tasks, audio recording,
   submission state, evaluation display, and coaching interaction.

2. **Backend AI service**
   A FastAPI service that exposes transcription, evaluation, coaching, and
   health endpoints. This layer owns the main domain logic.

3. **Knowledge and retrieval layer**
   A ChromaDB-backed vector store containing chunked educational material. It
   provides evidence for RAG-based evaluation and coaching.

High-level request flow:

```text
Learner records audio in frontend
  -> frontend stores submission metadata and audio locally
  -> frontend calls FastAPI /api/transcribe
  -> backend sends audio to KISSKI/SAIA transcription endpoint
  -> frontend calls FastAPI /api/evaluate/full
  -> backend retrieves educational evidence from ChromaDB
  -> backend calls the configured LLM with transcript + evidence + rubric
  -> backend validates and resolves the result
  -> frontend displays evaluation and enables coaching
  -> frontend calls FastAPI /api/coach for follow-up explanations
```

## Backend Package Structure

The backend lives under:

```text
backend/src/examiner_coach/
├── main.py                  # Creates the FastAPI app, configures CORS/logging, and registers active routes
├── config.py                # Central settings: API keys, model names, environment, and knowledge-base paths
├── api/                     # HTTP-facing layer: schemas and route handlers
│   ├── schemas.py           # Pydantic request/response models shared by routes and services
│   └── routes/              # FastAPI endpoint modules
│       ├── audio.py         # /api/transcribe: accepts audio upload and returns transcript + duration
│       ├── evaluation.py    # /api/evaluate: runs the RAG evaluation pipeline
│       ├── coaching.py      # /api/coach: answers follow-up questions using transcript, evaluation, and evidence
│       └── health.py        # /api/health: simple service availability check
├── services/                # Core backend logic and AI workflows
│   ├── transcription.py     # Calls the KISSKI/SAIA transcription endpoint and validates transcript output
│   ├── rag_pipeline.py      # Main RAG pipeline: normalization, retrieval, reranking, LLM scoring, parsing
│   ├── evaluation_prompt.py # Evaluation rubric, scoring criteria, and evaluation prompt construction
│   ├── coaching_prompt.py   # Coaching prompt construction and structured coaching response contract
│   └── document_manager.py  # Knowledge-base ingestion: parse, clean, chunk, embed, and index documents
├── db/                      # Persistence adapters
│   └── vector_store.py      # ChromaDB client, collection access, upsert, query, delete, and reset operations
└── utils/                   # Shared helper functions
    ├── audio_utils.py       # Audio duration extraction and audio-related utilities
    └── i18n.py              # Resolves bilingual backend objects into one display language
```

### `main.py`

`main.py` is the FastAPI application factory. It creates the app, configures
CORS, sets logging, and registers active routers.

Active route groups:

- `GET /api/health`: basic service availability check.
- `POST /api/transcribe`: audio transcription.
- `POST /api/evaluate`: RAG-based transcript evaluation.
- `POST /api/coach`: conversational coaching based on transcript, evaluation,
  and retrieved evidence.

The application factory pattern keeps app construction testable and avoids
placing business logic in the server entry point.

### `config.py`

`config.py` centralizes runtime configuration using Pydantic settings. It loads
environment variables from the project `.env` file and defines:

| Setting group | Examples |
| --- | --- |
| KISSKI / SAIA access | `kisski_api_key`, `kisski_base_url`, `kisski_voice_base_url` |
| Model selection | LLM, embedding, and Whisper model names |
| Knowledge paths | raw knowledge directory, vector database directory, registry path |
| Runtime behavior | app environment, log level, CORS origins |

This module is imported throughout the backend so model names, API bases, and
storage paths stay consistent.

## Backend API Layer

The `api/` package contains HTTP-facing code: request validation, response
models, and route handlers. It deliberately stays thin. Most domain behavior is
delegated to `services/`.

### `api/schemas.py`

`schemas.py` defines the backend contract using Pydantic models.

Key schema groups:

| Group | Important models |
| --- | --- |
| Shared language support | `Language` |
| Transcription | `TranscriptionResponse` |
| Evaluation input/output | `EvaluationRequest`, `EvaluationResult`, `ResolvedEvaluationResult`, `CriterionResult` |
| Coaching input/output | `CoachingRequest`, `CoachingResponse`, `ResolvedCoachingResponse`, `CoachingSessionSummary` |
| Health/documents | Lightweight response models |

The backend uses a two-step language design:

1. Internally, evaluation and coaching can hold bilingual text fields.
2. Before returning to the frontend, `utils/i18n.py` resolves the bilingual
   object into a single requested display language.

This allows the backend to preserve multilingual results without regenerating
the evaluation.

### `api/routes/audio.py`

`audio.py` exposes:

```text
POST /api/transcribe
```

Responsibilities:

- Accept uploaded audio as multipart form data.
- Read file bytes.
- Pass bytes to `services/transcription.py`.
- Convert validation or upstream transcription failures into HTTP errors.

The route itself does not call external APIs directly; it delegates that to the
transcription service.

### `api/routes/evaluation.py`

`evaluation.py` exposes:

```text
POST /api/evaluate
POST /api/evaluate/full
```

Responsibilities:

- Validate transcript, duration, and requested output language.
- Call `evaluate_transcript()` from `services/rag_pipeline.py`.
- Resolve the canonical bilingual result into the requested language.
- Return either a validated `ResolvedEvaluationResult` or the canonical
  bilingual `EvaluationResult`.

This is the main production entry point for feedback scoring.

### `api/routes/coaching.py`

`coaching.py` exposes:

```text
POST /api/coach
```

Responsibilities:

- Accept the original transcript, previous evaluation, current user question,
  optional conversation history, and optional rolling session summary.
- Retrieve relevant knowledge-base evidence using the RAG pipeline.
- Build coaching messages with `services/coaching_prompt.py`.
- Call the configured LLM.
- Parse the JSON response into a structured coaching object.
- Attach citations only to retrieved evidence items selected by the model.
- Resolve the answer to the requested language.

The coaching route is intentionally more conversational than evaluation, but it
is still grounded in three inputs:

1. Original examiner transcript.
2. Previous structured evaluation.
3. Retrieved educational evidence.

## Service Layer

The `services/` package contains the backend's core logic. This is where most
of the project-specific architecture lives.

### `services/transcription.py`

This module converts uploaded audio bytes into a transcript.

Processing steps:

```text
audio bytes
  -> temporary audio file
  -> duration extraction
  -> KISSKI/SAIA Whisper-compatible transcription request
  -> text validation
  -> TranscriptionResponse
```

Important design choices:

- The audio file is written temporarily so duration can be measured reliably.
- The temporary file is removed in a `finally` block.
- Empty uploads and empty transcription results are treated as validation
  failures.
- Upstream transcription errors are logged with status and response details.

### `services/rag_pipeline.py`

`rag_pipeline.py` is the central backend module. It owns the evaluation RAG
workflow and shared retrieval utilities used by coaching.

Major responsibilities:

- Normalize German or English transcripts for retrieval.
- Build retrieval queries from transcript and optional user query.
- Retrieve candidate chunks from ChromaDB.
- Optionally use HyDE-style retrieval.
- Deduplicate retrieval results.
- Rerank candidates using lightweight domain heuristics.
- Build formatted RAG context for prompts.
- Call the LLM for feedback evaluation.
- Parse and validate the model response.
- Compute final aggregate scores.

Core data structures:

| Structure | Purpose |
| --- | --- |
| `RetrievalInput` | Transcript plus optional user query |
| `RetrievalConfig` | Retrieval mode, candidate pool size, final context size, normalization, reranking |
| RAG context dictionary | Query, final evidence results, formatted context text, retrieval metadata |

Evaluation pipeline:

```text
transcript
  -> strip and validate
  -> translate/normalize to English when needed
  -> build criterion-aware retrieval query
  -> embed query
  -> query ChromaDB
  -> rerank retrieved chunks
  -> format evidence context
  -> build evaluation prompt
  -> call LLM
  -> parse JSON output
  -> validate against Pydantic schemas
  -> compute overall score and criteria_met
  -> return EvaluationResult
```

Retrieval modes:

| Mode | Behavior |
| --- | --- |
| `none` | Skip retrieval and evaluate without evidence context |
| `direct` | Embed the transcript/query and retrieve directly from ChromaDB |
| `hyde` | Combine direct retrieval with a generated hypothetical evidence passage |

The default production behavior is direct retrieval with criterion-aware query
construction, English normalization, and quality reranking.

### Retrieval Reranking

The first retrieval pass is vector-based. After that, the backend applies
domain-specific heuristics to improve evidence quality.

Positive signals include:

- Sections about feedback guidance, recommendations, rules, or practical tips.
- Keywords related to specificity, direct observation, objective tone,
  changeable behavior, and action plans.
- Chunks classified as guidance.

Negative signals include:

- References, bibliographies, DOI-heavy chunks, abstracts, and generic overview
  sections.
- Chunks marked as low-value during ingestion.

This keeps the final prompt focused on practical educational guidance rather
than bibliographic noise.

### `services/evaluation_prompt.py`

This module owns the evaluation rubric and prompt contract.

It defines six feedback quality criteria:

| Criterion ID | Meaning |
| --- | --- |
| `specific_behavior` | Names concrete observed behavior |
| `timely_contextual` | Anchored to the current station/context |
| `objective_tone` | Uses objective, non-judgmental wording |
| `strength_mentioned` | Explicitly identifies a strength |
| `improvement_area` | Identifies a changeable area for improvement |
| `improvement_plan` | Provides concrete next steps or an action plan |

Each criterion includes:

- Bilingual label.
- Guidance for judging.
- Scoring anchors at 0, 50, 70, 85, and 100.

The module also provides:

- `format_retrieved_context()` for inserting evidence into the prompt.
- Prompt-building helpers.
- Score aggregation helpers such as `compute_overall_score()` and
  `compute_criteria_met()`.

The LLM is instructed to return structured JSON. `rag_pipeline.py` then parses
that JSON and applies backend-side validation and fallback behavior.

### `services/coaching_prompt.py`

This module builds the prompt for conversational coaching.

Inputs:

- Original transcript.
- Resolved evaluation result.
- Current user question.
- Recent conversation history.
- Rolling session summary.
- Retrieved evidence items.
- Desired output language.

The prompt asks the model to return JSON containing:

- English and German answer fields.
- Optional citation requests pointing to retrieved evidence IDs.
- Updated rolling session summary.

This lets the coaching route support multi-turn interaction while keeping
responses structured and display-language independent.

### `services/document_manager.py`

`document_manager.py` owns knowledge-base ingestion.

Document ingestion pipeline:

```text
source document
  -> KISSKI Docling/document conversion
  -> parser artifact cleanup
  -> markdown-header-aware chunking
  -> recursive text splitting
  -> chunk metadata classification
  -> embedding generation
  -> ChromaDB upsert
  -> registry update
```

Important behaviors:

- Uses Markdown headers to preserve document structure.
- Adds metadata such as source, header labels, chunk type, and low-value flags.
- Formats passages and queries using E5-style prefixes:
  - `passage: ...` for stored chunks.
  - `query: ...` for retrieval queries.
- Tracks indexed files in `knowledge_base/registry.json`.

This module is used mainly by ingestion scripts, not by the request-time
evaluation endpoint.

## Database and Retrieval Storage

### `db/vector_store.py`

The vector store layer wraps ChromaDB access.

Responsibilities:

- Create a persistent Chroma client.
- Create or retrieve the `examiner_coach_knowledge` collection.
- Upsert embedded chunks.
- Query chunks by embedding.
- Convert Chroma distances into relevance scores.
- Delete chunks by source.
- Reset the vector store for re-indexing.

Persistent data is stored under:

```text
knowledge_base/processed/
```

The collection uses cosine distance.

## Utility Layer

### `utils/audio_utils.py`

Audio utility code supports the transcription pipeline, especially duration
extraction from uploaded recordings.

### `utils/i18n.py`

`i18n.py` resolves canonical bilingual backend objects into single-language
responses.

Examples:

- `EvaluationResult` -> `ResolvedEvaluationResult`
- `CoachingResponse` -> `ResolvedCoachingResponse`

This module keeps language selection separate from evaluation and coaching
logic.

## Backend Request Flows

### 1. Transcription Flow

```text
Frontend submission processor
  -> POST /api/transcribe
  -> api/routes/audio.py
  -> services/transcription.py
  -> KISSKI/SAIA audio transcription endpoint
  -> TranscriptionResponse
```

Output:

```text
{
  "transcript": "...",
  "duration_seconds": 123.4
}
```

### 2. Evaluation Flow

```text
Frontend submission processor
  -> POST /api/evaluate
  -> api/routes/evaluation.py
  -> services/rag_pipeline.py
  -> db/vector_store.py
  -> services/evaluation_prompt.py
  -> KISSKI LLM endpoint
  -> utils/i18n.py
  -> ResolvedEvaluationResult
```

The evaluation result contains:

- Original transcript.
- Recording duration.
- Overall percentage score.
- Short summary.
- Number of criteria met.
- Per-criterion scores and suggestions.
- Key improvement suggestion.

### 3. Coaching Flow

```text
Frontend coaching request
  -> POST /api/coach
  -> api/routes/coaching.py
  -> services/rag_pipeline.py for evidence retrieval
  -> services/coaching_prompt.py
  -> KISSKI LLM endpoint
  -> structured JSON parsing
  -> utils/i18n.py
  -> ResolvedCoachingResponse
```

The coaching response contains:

- Natural-language answer in the requested display language.
- Optional citations to retrieved evidence.
- Updated rolling session summary for future turns.

## Frontend Role

The frontend is intentionally lighter than the backend. It is responsible for
user interaction and local workflow orchestration.

Relevant frontend areas:

```text
frontend/app/
├── login/page.tsx
├── app/page.tsx
└── api/
    ├── submissions/
    ├── coach/
    ├── videos/
    ├── status/
    └── auth/

frontend/components/
├── AppShell.tsx
├── AudioRecorder.tsx
├── FeedbackPanel.tsx
├── CoachingPanel.tsx
├── EvaluationPanel.tsx
├── VideoPlayer.tsx
└── VideoSidebar.tsx
```

The most important frontend integration path is:

```text
AppShell
  -> /api/submissions
  -> /api/submissions/{id}/process
  -> FastAPI /api/transcribe
  -> FastAPI /api/evaluate
```

The frontend's Next.js API routes act as a backend-for-frontend:

- Store uploaded audio and submission metadata locally.
- Check session authorization.
- Proxy AI-related calls to the FastAPI backend.
- Poll submission state for the UI.

## Knowledge Base and Scripts

The knowledge base is managed outside the request path by scripts in
`backend/scripts/`.

Important scripts:

| Script | Purpose |
| --- | --- |
| `ingest_documents.py` | Parse, chunk, embed, and index source documents |
| `reset_vector_store.py` | Clear the ChromaDB store before re-indexing |
| `debug_chunks.py` | Inspect generated chunks |
| `evaluate_sample.py` | Run sample evaluation |
| `compare_rag_variants.py` | Compare retrieval configurations |

These scripts support development, reproducibility, and RAG tuning without
adding complexity to the production request handlers.

## External Dependencies

Important backend dependencies:

| Dependency | Role |
| --- | --- |
| FastAPI | HTTP API framework |
| Pydantic / pydantic-settings | Request validation and configuration |
| OpenAI client | KISSKI-compatible chat and embedding API access |
| httpx | Direct HTTP calls, especially audio transcription and document conversion |
| ChromaDB | Persistent vector database |
| LangChain text splitters | Markdown-aware and recursive document chunking |
| pytest | Backend tests |

The configured external AI services are:

- KISSKI-compatible chat completion endpoint.
- KISSKI-compatible embedding endpoint.
- SAIA/KISSKI Whisper-compatible transcription endpoint.
- KISSKI document conversion endpoint for knowledge-base ingestion.

## Testing Scope

Backend tests currently cover selected core units:

```text
backend/tests/
├── test_document_manager.py
├── test_rag_pipeline.py
└── test_transcription.py
```

The existing tests focus on:

- Retrieval configuration behavior.
- RAG context behavior when retrieval is disabled.
- Document/chunking behavior.
- Transcription service behavior.

Because the backend relies on external AI services, many integration paths are
best tested with mocked clients or controlled sample data.

## Architectural Strengths

- The FastAPI route layer is thin and delegates domain logic to services.
- Evaluation criteria are centralized and explicit.
- RAG retrieval is configurable and can be benchmarked independently.
- Document ingestion is separated from request-time evaluation.
- Bilingual output is handled structurally rather than through ad hoc string
  switching.
- The vector store layer is isolated behind a small database module.
- Coaching reuses retrieval infrastructure while keeping a separate prompt and
  response contract.

## Current Boundaries and Considerations

- Frontend state and submissions are stored locally in JSON files rather than a
  production database.
- The backend depends on external KISSKI/SAIA services for transcription,
  embeddings, document conversion, and LLM responses.
- The active document management HTTP router is not registered in `main.py`.
  Knowledge-base management is currently script-driven.
- RAG quality depends heavily on the indexed source documents and chunk
  metadata.
- LLM responses are required to be JSON, so parsing and fallback logic are
  important reliability safeguards.

## Summary

The backend is organized as a modular AI service:

```text
FastAPI routes
  -> Pydantic schemas
  -> service layer
  -> vector store and external AI services
  -> structured validated responses
```

The most important backend flow is the RAG evaluation pipeline. It transforms a
spoken feedback transcript into a validated, criterion-based assessment by
combining transcript normalization, evidence retrieval, prompt construction,
LLM scoring, JSON parsing, and bilingual response resolution.

The coaching pipeline builds on the same foundation, using the transcript,
evaluation result, conversation history, and retrieved evidence to provide
practical follow-up guidance for examiners.
