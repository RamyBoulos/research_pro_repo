"""
evaluation_prompt.py

Builds the bilingual, percentage-based feedback-evaluation prompt for the
Kisski LLM. This module owns:
  - the canonical feedback quality criteria definitions
  - the prompt builder that combines transcript + RAG context into messages
  - the JSON output schema contract the LLM must satisfy
  - helpers to compute overall_score and criteria_met from raw criterion scores

What this module does NOT do:
  - call the LLM
  - query ChromaDB
  - parse or validate Pydantic models
"""

from __future__ import annotations


# ── Constants ────────────────────────────────────────────────

# Percentage threshold above which a criterion counts as "met".
CRITERIA_MET_THRESHOLD: float = 70.0

# Target feedback duration in seconds (2 minutes).
TARGET_DURATION_SECONDS: float = 120.0

# Maximum number of words in a quoted excerpt from the transcript.
MAX_QUOTE_WORDS: int = 25


# ── Criteria definitions ─────────────────────────────────────

FEEDBACK_QUALITY_CRITERIA: list[dict] = [
    {
        "id": "specific_behavior",
        "label": {
            "en": "Specific observed behavior named",
            "de": "Konkretes beobachtetes Verhalten benannt",
        },
        "guidance": (
            "Did the examiner explicitly name a specific, observable action the "
            "student performed rather than giving only a vague impression or "
            "general praise? Look for references to concrete moments, such as a "
            "specific question asked, an examination step taken, or a "
            "communication act observed."
        ),
        "scoring_anchors": {
            0: "No specific behavior named at all. Only vague or general statements.",
            50: (
                "At least one behavior referenced but described imprecisely or "
                "without enough context to identify what exactly happened."
            ),
            100: (
                "One or more concrete, observable student actions named clearly "
                "and unambiguously, tied to a specific moment in the station."
            ),
        },
    },
    {
        "id": "timely_contextual",
        "label": {
            "en": "Timely and contextual",
            "de": "Zeitnah und kontextuell",
        },
        "guidance": (
            "Was the feedback clearly anchored to what just happened at this "
            "specific OSCE station? Generic feedback that could apply to any "
            "student or any station scores low here."
        ),
        "scoring_anchors": {
            0: (
                "Feedback is completely decontextualized. No reference to the "
                "specific station, scenario, or what the student actually did."
            ),
            50: (
                "Some contextual reference is present but the feedback could "
                "largely apply to any student or any station."
            ),
            100: (
                "Feedback is clearly and specifically tied to this student's "
                "performance at this station. The scenario context is evident."
            ),
        },
    },
    {
        "id": "objective_tone",
        "label": {
            "en": "Objective and non-evaluative tone",
            "de": "Objektiver, nicht wertender Ton",
        },
        "guidance": (
            "Did the examiner stick to describing observable facts and behaviors, "
            "avoiding personal judgments about the student as a person? Watch for "
            "judgmental language versus descriptive language."
        ),
        "scoring_anchors": {
            0: (
                "Predominantly judgmental, personal, or purely evaluative language "
                "throughout. No objective behavioral description."
            ),
            50: (
                "Mostly objective with one or two clearly evaluative or judgmental "
                "phrases that undermine the tone."
            ),
            100: (
                "Consistently objective throughout. All statements describe "
                "observable behaviors without personal judgment."
            ),
        },
    },
    {
        "id": "strength_mentioned",
        "label": {
            "en": "Strength explicitly mentioned",
            "de": "Stärke explizit benannt",
        },
        "guidance": (
            "Did the examiner explicitly name at least one thing the student did "
            "well, with a concrete example? Vague praise such as 'good job' does "
            "not count."
        ),
        "scoring_anchors": {
            0: "No strength mentioned at all, or only vague non-specific praise.",
            50: (
                "A strength is mentioned but without a concrete example or "
                "specific behavior reference."
            ),
            100: (
                "At least one clear, specific strength named with a concrete "
                "example of what the student did that constitutes that strength."
            ),
        },
    },
    {
        "id": "improvement_area",
        "label": {
            "en": "Area for improvement with changeable behavior",
            "de": "Verbesserungsbereich mit änderbarem Verhalten",
        },
        "guidance": (
            "Did the examiner identify an area for improvement and describe it as "
            "a specific, changeable behavior rather than a personality trait or "
            "fixed attribute?"
        ),
        "scoring_anchors": {
            0: (
                "No improvement area mentioned, or only a vague/general critique "
                "with no actionable behavior identified."
            ),
            50: (
                "An improvement area is named but described as a trait or attitude "
                "rather than a specific changeable behavior."
            ),
            100: (
                "At least one concrete, specific improvement described as an "
                "actionable behavior change the student can make."
            ),
        },
    },
    {
        "id": "improvement_plan",
        "label": {
            "en": "Improvement plan discussed",
            "de": "Verbesserungsplan besprochen",
        },
        "guidance": (
            "Did the examiner offer concrete next steps, a suggested practice "
            "strategy, or an action plan the student can follow? This goes beyond "
            "identifying a problem."
        ),
        "scoring_anchors": {
            0: "No next steps, suggestions, or action plan of any kind.",
            50: (
                "A vague suggestion is present, but without enough specificity to "
                "be actionable."
            ),
            100: (
                "At least one concrete, specific next step or action plan offered "
                "that the student can act on immediately."
            ),
        },
    },
]


def _criterion_ids() -> list[str]:
    return [criterion["id"] for criterion in FEEDBACK_QUALITY_CRITERIA]


# ── Context formatter ────────────────────────────────────────

def format_retrieved_context(results: list[dict]) -> str:
    """
    Format RAG retrieval results into a labeled evidence block for the prompt.
    """
    if not results:
        return "No relevant evidence retrieved from the knowledge base."

    sections: list[str] = []
    for index, result in enumerate(results, start=1):
        source = result.get("source", "unknown")
        relevance = result.get("relevance", 0.0)
        text = result.get("text", "").strip()
        sections.append(
            f"[Evidence {index} | source: {source} | relevance: {relevance:.3f}]\n{text}"
        )

    return "\n\n".join(sections)


# ── Criteria formatter ───────────────────────────────────────

def format_criteria_for_prompt() -> str:
    """
    Format criteria, bilingual labels, guidance, and score anchors for the LLM.
    """
    lines: list[str] = []
    for criterion in FEEDBACK_QUALITY_CRITERIA:
        lines.append(f"CRITERION: {criterion['id']}")
        lines.append(f"Label (EN): {criterion['label']['en']}")
        lines.append(f"Label (DE): {criterion['label']['de']}")
        lines.append(f"Guidance: {criterion['guidance']}")
        lines.append("Scoring anchors:")
        for score, description in criterion["scoring_anchors"].items():
            lines.append(f"  {score}/100: {description}")
        lines.append("")

    return "\n".join(lines)


# ── JSON schema formatter ────────────────────────────────────

def format_json_schema() -> str:
    """
    Return the exact JSON output contract the LLM must produce.
    """
    criterion_ids = _criterion_ids()
    example_id = criterion_ids[0]

    return f"""{{
  "criteria": [
    {{
      "criterion_id": "{example_id}",
      "score_percent": 0,
      "comment": {{
        "en": "<1-2 sentence explanation of the score in English>",
        "de": "<1-2 sentence explanation of the score in German>"
      }},
      "quote": null
    }}
  ],
  "key_suggestion": {{
    "en": "<single most important improvement tip in English, 1-2 sentences>",
    "de": "<single most important improvement tip in German, 1-2 sentences>"
  }}
}}"""


# ── System prompt ────────────────────────────────────────────

def build_system_prompt() -> str:
    """
    Build the system prompt defining the evaluator role and scoring philosophy.
    """
    return f"""You are an expert evaluator of OSCE examiner feedback quality.

Your task is to evaluate the quality of the EXAMINER'S spoken feedback, not:
- the student's clinical performance,
- the correctness of clinical decisions in the station,
- or the overall OSCE encounter unless it is directly reflected in the feedback itself.

Use the retrieved evidence as the reference for what good feedback practice
looks like according to the literature. Compare the examiner's transcript
against that evidence.

SCORING PHILOSOPHY:
- Score each criterion as a whole-number integer from 0 to 100.
- Use the full range. Do not default to 0, 25, 50, 75, or 100 unless the
  evidence clearly supports that exact level.
- A score around 50 means partially demonstrated with clear gaps.
- A score around 70 means adequately demonstrated.
- A score around 85 means strongly demonstrated with only minor omissions.
- Base your scores only on what is observable in the transcript.

EVIDENCE USE:
- The transcript is the PRIMARY evidence.
- The retrieved evidence is SUPPORTING guidance for how to judge quality.
- Do not replace transcript evidence with general background knowledge.
- If evidence from the transcript is weak or absent, score conservatively.

QUOTE POLICY:
- Only include a quote if the criterion score is below 80 AND a specific
  excerpt from the transcript illustrates the issue clearly.
- Keep quotes under {MAX_QUOTE_WORDS} words.
- Preserve the meaning of the original transcript faithfully.
- If no relevant quote exists, set quote to null.

OUTPUT CONTRACT:
- Return ONLY a valid JSON object matching the schema exactly.
- No preamble, no explanation, no markdown fences.
- Do not include overall_score or criteria_met — these are computed externally.
- Return score_percent values as integers, not decimals.
- All comment and key_suggestion fields must be present in both 'en' and 'de'.
- If quote is present, it must contain both 'en' and 'de'. Otherwise set quote to null.
- Criteria must appear in this exact order: {', '.join(_criterion_ids())}"""


# ── Duration helper ──────────────────────────────────────────

def _format_duration_note(duration_seconds: float) -> str:
    """
    Format a human-readable note about recording duration for context only.
    Duration should inform completeness judgments when clearly relevant, but it
    is not itself a separate scoring criterion.
    """
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)
    duration_str = f"{minutes}:{seconds:02d}"
    target_str = f"{int(TARGET_DURATION_SECONDS // 60)}:00"

    if duration_seconds < 30:
        return (
            "WARNING: The recording is very short (under 30 seconds). This may "
            "indicate a technical issue or extremely minimal feedback. Consider "
            "this only insofar as it affects the completeness of the feedback."
        )
    if duration_seconds < 60:
        return (
            f"The feedback was significantly shorter than the {target_str} target "
            f"(actual: {duration_str}). This may affect completeness, but do not "
            "penalize duration by itself."
        )
    if duration_seconds <= TARGET_DURATION_SECONDS + 15:
        return (
            f"The feedback duration ({duration_str}) is within the expected range "
            f"of the {target_str} target."
        )
    return (
        f"The feedback exceeded the {target_str} target (actual: {duration_str}). "
        "This is contextual information only and should not reduce scores by itself."
    )


# ── User prompt ──────────────────────────────────────────────

def build_user_prompt(
    transcript: str,
    context_text: str,
    duration_seconds: float,
) -> str:
    """
    Build the user prompt combining transcript, retrieved context, duration
    information, and exact evaluation instructions.
    """
    duration_note = _format_duration_note(duration_seconds)
    criteria_block = format_criteria_for_prompt()
    json_schema = format_json_schema()

    return f"""## RETRIEVED EVIDENCE

The following passages were retrieved from educational feedback literature and
guidance documents. Use them to calibrate what high-quality feedback looks like.

{context_text}

---

## TRANSCRIPT TO EVALUATE

The following is the examiner's spoken feedback to the student at the OSCE station.
Evaluate this feedback transcript against each criterion below.

{transcript.strip()}

---

## DURATION NOTE

{duration_note}

---

## EVALUATION TASK

Evaluate the transcript against the following feedback quality criteria. These
criteria are informed by the retrieved literature on effective feedback. Use
the retrieved evidence above as the scoring reference.

{criteria_block}

---

## REQUIRED OUTPUT

Return ONLY the following JSON object. No other text.

{json_schema}"""


# ── Main prompt builder ──────────────────────────────────────

def build_prompt(
    transcript: str,
    context_text: str,
    duration_seconds: float,
) -> list[dict[str, str]]:
    """
    Build the complete OpenAI/Kisski chat messages list for evaluation.
    """
    return [
        {
            "role": "system",
            "content": build_system_prompt(),
        },
        {
            "role": "user",
            "content": build_user_prompt(
                transcript=transcript,
                context_text=context_text,
                duration_seconds=duration_seconds,
            ),
        },
    ]


# ── Score helpers ────────────────────────────────────────────

def compute_overall_score(criterion_scores: list[float]) -> int:
    """
    Compute the overall score as the arithmetic mean of all criterion scores,
    rounded to the nearest whole number.
    """
    if not criterion_scores:
        return 0
    return round(sum(criterion_scores) / len(criterion_scores))


def compute_criteria_met(criterion_scores: list[float]) -> int:
    """
    Count how many criteria meet or exceed the configured threshold.
    """
    return sum(1 for score in criterion_scores if score >= CRITERIA_MET_THRESHOLD)
