from examiner_coach.api.routes.coaching import (
    apply_citation_policy,
    classify_coaching_intent,
)
from examiner_coach.api.schemas import (
    CoachingCitation,
    CoachingResponse,
    CoachingSessionSummary,
    Language,
)


def _coaching_response_with_citation() -> CoachingResponse:
    return CoachingResponse(
        answer={
            Language.EN: "Use more specific examples.",
            Language.DE: "Nutzen Sie spezifischere Beispiele.",
        },
        citations=[
            CoachingCitation(
                source="feedback.pdf",
                quote={
                    Language.EN: "Feedback should be specific.",
                    Language.DE: "Feedback should be specific.",
                },
            )
        ],
        updated_session_summary=CoachingSessionSummary(language=Language.DE),
    )


def test_classify_coaching_intent_handles_social_turns() -> None:
    assert classify_coaching_intent("Thank you!") == "social"
    assert classify_coaching_intent("Danke.") == "social"


def test_classify_coaching_intent_handles_off_topic_turns() -> None:
    assert classify_coaching_intent("What is the temperature today?") == "off_topic"
    assert classify_coaching_intent("Wie ist das Wetter morgen?") == "off_topic"


def test_classify_coaching_intent_handles_rewrite_without_sources() -> None:
    assert (
        classify_coaching_intent("Can you rewrite this feedback more constructively?")
        == "rewrite_request"
    )
    assert (
        classify_coaching_intent("Kannst du das besser formulieren?")
        == "rewrite_request"
    )


def test_classify_coaching_intent_allows_explicit_evidence_questions() -> None:
    assert (
        classify_coaching_intent("Which sources support this?")
        == "evidence_question"
    )
    assert (
        classify_coaching_intent("Warum wurde Spezifität so bewertet?")
        == "evidence_question"
    )


def test_apply_citation_policy_removes_citations_when_not_required() -> None:
    coaching = _coaching_response_with_citation()

    result = apply_citation_policy(coaching, "social")

    assert result.citations == []


def test_apply_citation_policy_removes_citations_for_rewrites() -> None:
    coaching = _coaching_response_with_citation()

    result = apply_citation_policy(coaching, "rewrite_request")

    assert result.citations == []


def test_apply_citation_policy_keeps_citations_for_evidence_questions() -> None:
    coaching = _coaching_response_with_citation()

    result = apply_citation_policy(coaching, "evidence_question")

    assert len(result.citations) == 1


def test_apply_citation_policy_keeps_citations_for_coaching_questions() -> None:
    coaching = _coaching_response_with_citation()

    result = apply_citation_policy(coaching, "coaching_question")

    assert len(result.citations) == 1
