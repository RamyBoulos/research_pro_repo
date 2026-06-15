"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  CoachingMessage,
  CoachingSessionSummary,
  Language,
  ResolvedCoachingResponse,
  ResolvedEvaluationResult,
} from "@/types/evaluation";
import { useLanguage } from "@/lib/LanguageProvider";

type ChatEntry =
  | { role: "user"; content: string }
  | {
      role: "assistant";
      content: string;
      citations: ResolvedCoachingResponse["citations"];
    };

const INITIAL_PROMPTS: Record<Language, string[]> = {
  de: [
    "Erkläre meine Bewertung",
    "Was sollte ich zuerst verbessern?",
    "Zeig mir eine stärkere Version",
    "Warum war das nicht spezifisch genug?",
    "Gib mir ein kurzes gutes Beispiel",
  ],
  en: [
    "Explain my score",
    "What should I improve first?",
    "Show me a stronger version",
    "Why was this not specific enough?",
    "Give me a short good example",
  ],
};

const DEFAULT_SUMMARY: Record<Language, CoachingSessionSummary> = {
  de: {
    language: "de",
    learner_needs: [],
    main_weaknesses: [],
    explained_criteria: [],
    rewrite_examples_given: [],
    current_focus: null,
    open_questions: [],
  },
  en: {
    language: "en",
    learner_needs: [],
    main_weaknesses: [],
    explained_criteria: [],
    rewrite_examples_given: [],
    current_focus: null,
    open_questions: [],
  },
};

interface CoachingPanelProps {
  transcript: string;
  evaluation: ResolvedEvaluationResult;
}

export default function CoachingPanel({ transcript, evaluation }: CoachingPanelProps) {
  const { t, language } = useLanguage();
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionSummary, setSessionSummary] = useState<CoachingSessionSummary>(
    DEFAULT_SUMMARY[language]
  );

  const initialPrompts = useMemo(
    () => INITIAL_PROMPTS[language] ?? INITIAL_PROMPTS.de,
    [language]
  );

  const evaluationContextKey = useMemo(
    () =>
      JSON.stringify({
        transcript,
        duration_seconds: evaluation.duration_seconds,
        overall_score: evaluation.overall_score,
        criteria_met: evaluation.criteria_met,
        criteria: evaluation.criteria.map((criterion) => [
          criterion.criterion_id,
          criterion.score_percent,
        ]),
      }),
    [transcript, evaluation]
  );

  useEffect(() => {
    setMessages([]);
    setInput("");
    setError(null);
    setSessionSummary(DEFAULT_SUMMARY[language]);
  }, [evaluationContextKey]);

  const handlePrompt = async (message: string) => {
    if (isLoading) {
      return;
    }

    const trimmed = message.trim();
    if (!trimmed) {
      return;
    }

    const conversation: CoachingMessage[] = messages.map((entry) => ({
      role: entry.role,
      content: entry.content,
    }));

    setError(null);
    setIsLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");

    try {
      const response = await fetch("/api/coach", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          transcript,
          duration_seconds: evaluation.duration_seconds,
          evaluation,
          user_message: trimmed,
          conversation,
          session_summary: sessionSummary,
          output_language: language,
        }),
      });

      const data = (await response.json()) as ResolvedCoachingResponse | { detail?: string };
      if (!response.ok) {
        throw new Error(("detail" in data && data.detail) || "Coaching failed.");
      }

      const coaching = data as ResolvedCoachingResponse;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: coaching.answer,
          citations: coaching.citations,
        },
      ]);
      setSessionSummary(coaching.updated_session_summary);
    } catch (err) {
      const messageText =
        err instanceof Error
          ? err.message
          : t("coachingChatTitle");
      setError(messageText);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="stack" style={{ gap: "12px" }}>
      <strong>{t("coachingChatTitle")}</strong>
      <p style={{ margin: 0, color: "var(--muted)" }}>
        {t("coachingHelpText")}
      </p>

      {messages.length === 0 ? (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {initialPrompts.map((prompt) => (
            <button
              key={prompt}
              className="btn secondary"
              onClick={() => void handlePrompt(prompt)}
              disabled={isLoading}
              style={{ textAlign: "left" }}
            >
              {prompt}
            </button>
          ))}
        </div>
      ) : null}

      {messages.length > 0 ? (
        <div
          className="stack"
          style={{
            gap: "12px",
            border: "1px solid rgba(15, 23, 42, 0.12)",
            borderRadius: "14px",
            padding: "14px",
          }}
        >
          {messages.map((entry, index) => (
            <div key={`${entry.role}-${index}`} className="stack" style={{ gap: "8px" }}>
              <div style={{ fontWeight: 600 }}>
                {entry.role === "user" ? t("coachingUserLabel") : "Coach"}
              </div>
              <div style={{ whiteSpace: "pre-wrap" }}>{entry.content}</div>
              {entry.role === "assistant" && entry.citations.length > 0 ? (
                <div
                  style={{
                    background: "rgba(15, 23, 42, 0.04)",
                    borderRadius: "10px",
                    padding: "12px",
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: "8px" }}>
                    {t("coachingSourcesLabel")}
                  </div>
                  <div className="stack" style={{ gap: "10px" }}>
                    {entry.citations.map((citation, citationIndex) => (
                      <div key={`${citation.source}-${citationIndex}`} style={{ fontSize: "0.95rem" }}>
                        <div>
                          <strong>{citation.source}</strong>
                          {citation.section ? ` · ${citation.section}` : ""}
                        </div>
                        {citation.quote ? (
                          <div style={{ color: "var(--muted)", fontStyle: "italic", marginTop: "4px" }}>
                            "{citation.quote}"
                          </div>
                        ) : null}
                        {citation.rationale ? (
                          <div style={{ marginTop: "4px" }}>{citation.rationale}</div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ))}
          {isLoading ? (
            <div style={{ color: "var(--muted)" }}>
              {t("coachingResponding")}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="stack" style={{ gap: "8px" }}>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={t("coachingInputPlaceholder")}
          style={{
            width: "100%",
            minHeight: "100px",
            padding: "12px",
            borderRadius: "8px",
            border: "1px solid var(--border)",
            fontSize: "15px",
            resize: "vertical",
            boxSizing: "border-box",
          }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center" }}>
          {error ? <span style={{ color: "#c0392b" }}>{error}</span> : <span />}
          <button
            className="btn"
            onClick={() => void handlePrompt(input)}
            disabled={isLoading || !input.trim()}
          >
            {t("coachingSendMessage")}
          </button>
        </div>
      </div>
    </div>
  );
}
