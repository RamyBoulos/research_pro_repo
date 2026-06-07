"""
evaluation_prompt.py

Builds the bilingual, integer-scored feedback-evaluation prompt for the
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
            70: (
                "At least one observable behavior is named clearly enough to be "
                "useful, but the example is limited in detail, context, or scope."
            ),
            85: (
                "More than one concrete observed behavior is identified, or one "
                "behavior is described with clear station-specific detail and "
                "little ambiguity."
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
            "en": "Contextual feedback",
            "de": "Kontextbezogenes Feedback",
        },
        "guidance": (
            "Was the feedback clearly anchored to this specific OSCE station, "
            "scenario, and student performance? Generic feedback that could "
            "apply to any student or any station scores low here."
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
            70: (
                "The feedback is clearly about this encounter and contains at "
                "least one station-relevant detail, but the contextual anchoring "
                "is still limited."
            ),
            85: (
                "The feedback is strongly anchored to this student's performance "
                "at this station, with multiple clear references to what happened "
                "in the encounter."
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
            70: (
                "Largely objective and behavior-focused, with only minor "
                "evaluative phrasing that does not dominate the feedback."
            ),
            85: (
                "Consistently objective and descriptive, with little or no drift "
                "into personal judgment or unsupported praise."
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
            70: (
                "At least one genuine strength is linked to an observable behavior, "
                "but the example is brief or only moderately detailed."
            ),
            85: (
                "A clear strength is explicitly named and supported by a concrete, "
                "relevant example from the station."
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
            70: (
                "An improvement area is described in changeable behavioral terms, "
                "but the recommendation remains somewhat broad or only partially specific."
            ),
            85: (
                "A clear, changeable behavior is identified as the improvement "
                "target, with specific wording that makes the issue easy to understand."
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
            70: (
                "At least one usable next step is offered, but it is still limited "
                "in detail, precision, or immediate practicality."
            ),
            85: (
                "A concrete next step or practice strategy is clearly stated and "
                "is well aligned with the observed weakness."
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
        for score, description in sorted(
            criterion["scoring_anchors"].items(),
            key=lambda item: item[0],
        ):
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
  "summary": {{
    "en": "<short overall summary in English, 2-4 sentences, natural prose>",
    "de": "<short overall summary in German, 2-4 sentences, natural prose>"
  }},
  "criteria": [
    {{
      "criterion_id": "{example_id}",
      "score_percent": "<integer 0-100>",
      "suggestion": {{
        "en": "<clear one-sentence improvement point in English>",
        "de": "<clear one-sentence improvement point in German>"
      }},
      "quote": null
    }}
  ],
  "key_suggestion": {{
    "en": "<single most important improvement tip in English, 1-2 sentences, natural prose>",
    "de": "<single most important improvement tip in German, 1-2 sentences, natural prose>"
  }}
}}"""


# ── System prompt ────────────────────────────────────────────

def build_system_prompt() -> str:
    return f"""You are a strict, calibrated evaluator of OSCE examiner feedback quality.

Your task is to evaluate the quality of the EXAMINER'S spoken feedback against
published criteria for effective clinical feedback. You are NOT evaluating the
student's performance.

INPUT NORMALIZATION:
- The transcript you receive has already been translated into English.
- Evaluate the feedback content in English only.
- Then generate the summary, criterion suggestions, and key_suggestion in both
  English and German.
- The same underlying feedback content must receive the same scores regardless
  of the language in which it was originally spoken.

CRITICAL SCORING RULE:
Most real-world examiner feedback is mediocre to average. Scores of 80+ must
be rare and fully justified by specific evidence from the transcript.
Default to skepticism, not generosity.

Before assigning any score above 70, you must be able to complete this sentence
using only words from the transcript:
"The examiner demonstrated this criterion by specifically saying: ..."
If you cannot complete that sentence, the score must be below 70.

LANGUAGE INVARIANCE REQUIREMENT:
The same feedback content must receive the same scores regardless of language.
If an English phrase would score 50, its German translation must also score 50.
Do not award higher scores to formally phrased German text unless the content
is genuinely stronger.

SCORE CALIBRATION — what each level means:
  0–20:  Criterion completely absent or violated
  21–40: Weak attempt, major gaps, mostly missing
  41–60: Partial demonstration, present but insufficient
  61–70: Adequate but not strong — crosses the minimum bar
  71–85: Clearly demonstrated with only minor gaps
  86–100: Exemplary — rare, requires strong specific evidence

COMMON SCORING ERRORS TO AVOID:
- Do NOT score "strength_mentioned" above 60 if the only praise is vague
  ("good job", "well done", "good performance", "I am satisfied").
  A scorable strength requires naming a SPECIFIC observable action.
- Do NOT score "specific_behavior" above 60 if the examiner only names
  a task category ("history taking", "examination") rather than a concrete
  observable moment.
- Do NOT score "improvement_plan" above 60 if the only suggestion is a
  general directive ("be more systematic", "practise more", "ask all points").
  A scorable plan requires a concrete, specific next step.
- Do NOT score "timely_contextual" above 80 unless the feedback references
  a specific moment, scenario detail, or student action from this particular
  station. This criterion is about contextual anchoring, not timing.

EVIDENCE USE:
- The transcript is the PRIMARY evidence. Read it literally.
- The retrieved evidence defines what good practice looks like.
- Compare what the examiner ACTUALLY SAID against the anchors.
- Do not infer intent. Score only what is observable.

QUOTE POLICY:
- Only include a quote if the criterion score is below 80 AND a specific
  excerpt illustrates the issue clearly.
- Keep quotes under {MAX_QUOTE_WORDS} words.
- If no relevant quote exists, set quote to null.

SUGGESTION POLICY:
- For every criterion, return one clear sentence of practical advice.
- Keep each suggestion concise, specific, and natural-sounding.
- Do not mention criterion ids such as "timely_contextual" in user-facing text.
- Phrase suggestions as improvement points, not labels or fragments.
- For "timely_contextual", focus the suggestion on adding concrete station,
  scenario, or student-performance details, for example what the student did,
  said, missed, or handled in this OSCE encounter.
- If the criterion is already strong, the suggestion may briefly reinforce the
  strength rather than correcting a weakness.

SUMMARY POLICY:
- Return one concise overall summary covering the main strengths and weaknesses
  across the full feedback.
- Keep it short and readable.

OUTPUT CONTRACT:
- Return ONLY a valid JSON object matching the schema exactly.
- No preamble, no explanation, no markdown fences.
- Do not include overall_score or criteria_met — computed externally.
- Return score_percent as integers.
- All summary, suggestion, and key_suggestion fields must be in both 'en' and 'de'.
- If quote is present it must contain both 'en' and 'de'. Otherwise null.
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

The following is an English-normalized version of the examiner's spoken feedback
to the student at the OSCE station. Evaluate this feedback transcript against
each criterion below.

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
