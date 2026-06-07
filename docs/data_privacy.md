# Data Privacy and Data Handling

## Purpose

This document describes how Examiner Coach handles data during the current
prototype workflow. It is intended for project documentation, technical review, and presentation contexts. It is not a formal legal privacy notice.

The system processes examiner training data, including audio recordings,
transcripts, evaluation outputs, and local session metadata. The main backend
processing is performed by the FastAPI service, while the frontend manages the
training workflow and local submission state.

## Data Processed by the System

The application may process the following data categories:

- Participant/session data: access code, entered participant name, generated
  session identifier, and local session token.
- Training task data: selected video identifier and station/category metadata.
- Audio data: recorded examiner feedback uploaded by the participant.
- Transcript data: text generated from the uploaded audio recording.
- Evaluation data: criterion-level scores, summary, suggestions, and quoted
  transcript excerpts where applicable.
- Coaching data: user questions, recent conversation history, coaching answers, citations, and rolling coaching summary.
- Operational data: timestamps, processing status, error messages, and backend logs.

## Runtime Data Flow

The main processing path is:

```text
Participant records feedback in the frontend
  -> frontend stores audio and submission metadata locally
  -> frontend sends audio to FastAPI /api/transcribe
  -> backend sends audio to the configured KISSKI/SAIA transcription endpoint
  -> backend returns transcript and duration
  -> frontend sends transcript to FastAPI /api/evaluate
  -> backend retrieves evidence from the local ChromaDB knowledge base
  -> backend sends transcript, retrieved evidence, and rubric to the LLM endpoint
  -> backend returns structured evaluation
  -> optional coaching requests are sent to FastAPI /api/coach
```

## Local Storage

In the current implementation, the frontend stores study workflow data locally under the frontend `data/` directory.

Typical local files include:

- `data/users.json`: configured access-code records.
- `data/sessions.json`: local session records.
- `data/submissions.json`: submission metadata, status, transcript, and
  evaluation result.
- `data/audio/`: uploaded audio recordings saved as local files.
- `data/videos.json`: local video metadata.

The backend stores the processed retrieval index under:

```text
knowledge_base/processed/
```

The knowledge-base registry is stored at:

```text
knowledge_base/registry.json
```

## External Service Processing

The backend is configured to use GWDG/KISSKI/SAIA API endpoints for:

- Audio transcription.
- Chat completion for evaluation and coaching.
- Embedding generation for retrieval.
- Document conversion during knowledge-base ingestion.

This means selected data leaves the local application environment during
processing:

- Audio files are sent to the configured transcription endpoint.
- Transcript text, retrieved evidence, and rubric instructions are sent to the
  configured LLM endpoint for evaluation.
- Coaching requests include the transcript, previous evaluation, conversation
  context, and retrieved evidence.
- Knowledge-base documents are sent to the document conversion endpoint during
  ingestion.

The exact data handling guarantees depend on the configured endpoint, selected
model, and institutional agreements. GWDG/KISSKI documentation distinguishes
between internally hosted models and external provider models, so this should
be checked for the concrete deployment.


## Retention and Deletion

The current prototype does not implement an automated retention policy.

Locally stored data remains present until it is manually deleted or the
deployment environment removes it. This includes uploaded audio recordings,
submission metadata, transcripts, and evaluation results.

For production or study deployment, a retention policy should define:

- How long audio recordings are kept.
- How long transcripts and evaluations are kept.
- Who can access local storage.
- How participant withdrawal or deletion requests are handled.
- Whether logs may contain processing errors or excerpts.


## Logging

The backend logs operational information such as request receipt, transcript
length, retrieval settings, and error details. Error logs may include upstream response snippets in failure cases.


## Knowledge Base Data

The knowledge base is separate from participant submissions. It contains
educational documents that are parsed, chunked, embedded, and stored in
ChromaDB.

Knowledge-base ingestion is script-driven. Documents are expected under:

```text
knowledge_base/raw/
```

The processed vector index is stored under:

```text
knowledge_base/processed/
```

Only the retrieved text chunks needed for evaluation or coaching are included
in LLM prompts at runtime.

## Recommended Deployment Safeguards

Before using the system in a live study or institutional setting, the following safeguards should be reviewed:

- Confirm the data processing terms of the configured GWDG/KISSKI/SAIA services
  and selected models.
- Use HTTPS for deployed frontend and backend traffic.
- Restrict access to local data directories or move storage to a managed
  database.
- Define a retention and deletion policy.
- Avoid collecting unnecessary identifiers.
- Provide participant-facing information about audio transcription and AI-based
  evaluation.
- Review whether transcripts, audio, and logs should be encrypted at rest.
- Establish a process for removing participant data after the study.

## Current Limitations

- Local JSON/file storage is used for frontend workflow state.
- There is no automated deletion or retention mechanism.
- Authentication is intentionally lightweight.
- External services receive audio, text, or documents depending on the
  processing step.
- This document describes technical behavior and should be reviewed by the
  relevant data protection or ethics contact before production use.
