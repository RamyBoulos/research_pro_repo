# Feedback Quality Instrument

## Purpose

This document describes the feedback-quality instrument implemented in
Examiner Coach. The instrument is used to evaluate spoken OSCE examiner
feedback and to generate targeted coaching suggestions.

The instrument is implemented in the backend in:

```text
backend/src/examiner_coach/services/evaluation_prompt.py
```

It is not intended to grade the student shown in the OSCE video. It evaluates
the quality of the examiner's feedback to that student.

## What Is Being Evaluated

The system evaluates whether the examiner's spoken feedback is useful,
specific, objective, and actionable. The transcript is assessed against six
criteria. Each criterion receives a percentage score from 0 to 100.

The output is designed for formative training. It should help examiners
understand what makes feedback educationally useful and how to improve their
next feedback attempt.

## Criteria

### 1. Specific observed behavior named

Backend ID:

```text
specific_behavior
```

This criterion checks whether the examiner names concrete, observable behavior from the student's performance. Feedback should refer to something the student actually did, such as a question asked, a physical examination step, a communication behavior, or a clinical action.

Low-scoring feedback is vague or global, for example general praise or
criticism without a clear behavioral reference.

High-scoring feedback clearly identifies one or more specific observed actions.

### 2. Contextual feedback

Backend ID:

```text
contextual
```

This criterion checks whether the feedback is anchored in the current OSCE
station, scenario, and student performance. Feedback should sound connected to
what the student did in this specific encounter rather than being reusable for
any student or any station.

Low-scoring feedback is generic and decontextualized.

High-scoring feedback clearly refers to what happened in the station.

### 3. Objective and non-evaluative tone

Backend ID:

```text
objective_tone
```

This criterion checks whether the examiner uses descriptive, behavior-focused
language instead of personal judgment. The emphasis is on observable facts and actions, not on labeling the student as good, bad, careless, confident, weak, or similar.

Low-scoring feedback relies heavily on judgmental or personality-focused
language.

High-scoring feedback describes behavior objectively and avoids unsupported
personal evaluation.

### 4. Strength explicitly mentioned

Backend ID:

```text
strength_mentioned
```

This criterion checks whether the examiner explicitly identifies something the student did well. A useful strength should be linked to an example or observed behavior.

Low-scoring feedback omits strengths or only gives vague praise.

High-scoring feedback names a concrete strength and explains what the student
did that made it effective.

### 5. Area for improvement with changeable behavior

Backend ID:

```text
improvement_area
```

This criterion checks whether the examiner identifies an improvement area in
terms of behavior the student can change. The focus should be on actions,
phrasing, sequence, structure, or clinical technique rather than fixed traits.

Low-scoring feedback gives only vague criticism or frames the issue as a
personal characteristic.

High-scoring feedback identifies a clear and changeable behavior.

### 6. Improvement plan discussed

Backend ID:

```text
improvement_plan
```

This criterion checks whether the examiner gives a concrete next step,
practice strategy, or action plan. It goes beyond naming a weakness and tells
the student what to do differently next time.

Low-scoring feedback contains no next step or only a vague suggestion.

High-scoring feedback offers a practical, specific, and immediately usable
improvement strategy.

## Scoring Model

Each criterion is scored on a 0 to 100 scale. The backend prompt provides
scoring anchors at:

```text
0, 50, 70, 85, 100
```

These anchors help the evaluator distinguish absent, partial, adequate, strong, and excellent evidence for each criterion.

The backend computes:

- `overall_score`: arithmetic mean of the six criterion scores.
- `criteria_met`: number of criteria with a score greater than or equal to the
  default threshold (`score >= 70`).
- `total_criteria`: the number of active criteria, currently six.

The current threshold for a criterion to count as met is:

```text
score >= 70
```

## Interpretation

Scores should be interpreted as formative guidance rather than summative
assessment.

Suggested interpretation:

- 0-49: criterion is absent or only minimally present.
- 50-69: criterion is partially present but needs clearer execution.
- 70-84: criterion is met at a usable level.
- 85-100: criterion is strong and well demonstrated.

The system also returns a short suggestion for each criterion. When available, it may include a quote from the transcript, especially when a lower score needs to be explained with a concrete example.

## Role of RAG Evidence

The evaluation is supported by retrieval-augmented generation. Before the LLM
evaluates the transcript, the backend retrieves relevant educational guidance
from the local ChromaDB knowledge base.

The retrieved evidence is used to ground the evaluation in feedback education
principles. It does not replace the transcript. The transcript remains the main object being evaluated.

The retrieval pipeline can:

- Normalize transcripts to English for retrieval.
- Build criterion-aware queries.
- Retrieve candidate chunks from ChromaDB.
- Rerank evidence to prefer practical guidance over references or generic
  sections.
- Format the final evidence context for the evaluation prompt.

## Output Structure

The backend returns a structured evaluation containing:

- Original transcript.
- Audio duration.
- Overall score.
- Short summary.
- Number of criteria met.
- Per-criterion score, label, suggestion, and optional quote.
- One key suggestion for the examiner.

The canonical backend result can hold bilingual text. Before returning to the
frontend, the result is resolved to the requested display language.

## Example Use in Coaching

The coaching endpoint reuses the evaluation result. When the learner asks a
follow-up question, the backend provides the original transcript, structured
evaluation, recent conversation history, and retrieved evidence to the coaching
prompt.

This allows the coach to explain why a criterion received a given score and to propose better feedback wording.

## Boundaries

The instrument evaluates feedback quality, not clinical correctness of the
student's performance.

It does not replace expert human judgment. It is designed to support practice, self-reflection, and structured coaching.

The quality of the output depends on:

- The clarity and completeness of the audio recording.
- The accuracy of transcription.
- The quality of the indexed knowledge base.
- The calibration of the LLM response to the scoring anchors.
- The validity of the chosen criteria for the intended training context.

For formal assessment or research use, the criteria and scoring behavior should be reviewed by domain experts and validated against human ratings.
