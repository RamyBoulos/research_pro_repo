"use client";

import { useState } from "react";
import { useLanguage } from "@/lib/LanguageProvider";
import { EVALUATION_QUESTIONS } from "@/lib/translations";

type LikertQuestion = {
  type: "likert";
  text: string;
  low: string;
  high: string;
};

type TextQuestion = {
  type: "text";
  text: string;
};

type Question = LikertQuestion | TextQuestion;

interface EvaluationPanelProps {
  onComplete?: () => void;
}

export default function EvaluationPanel({ onComplete }: EvaluationPanelProps) {
  const { language, t } = useLanguage();
  const QUESTIONS: Question[] = EVALUATION_QUESTIONS[language];
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<(number | string | null)[]>(
    Array(QUESTIONS.length).fill(null)
  );
  const [submitted, setSubmitted] = useState(false);

  const question = QUESTIONS[step];
  const current = answers[step];
  const isLast = step === QUESTIONS.length - 1;

  const setAnswer = (value: number | string) => {
    setAnswers((prev) => {
      const next = [...prev];
      next[step] = value;
      return next;
    });
  };

  const handleSubmit = async () => {
    await fetch("/api/evaluations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    });
    setSubmitted(true);
    onComplete?.();
  };

  if (submitted) {
    return (
      <div className="panel fade-in" style={{ textAlign: "center" }}>
        <h2 style={{ fontFamily: "var(--font-fraunces)", marginTop: 0 }}>{t("thanks")}</h2>
        <p style={{ color: "var(--muted)" }}>{t("answersSaved")}</p>
        <button
          className="btn secondary"
          style={{ marginTop: "16px" }}
          onClick={() => {
            setStep(0);
            setAnswers(Array(QUESTIONS.length).fill(null));
            setSubmitted(false);
          }}
        >
          {t("restart")}
        </button>
      </div>
    );
  }

  return (
    <div className="panel fade-in stack">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontFamily: "var(--font-fraunces)", margin: 0 }}>{t("evaluationHeader")}</h2>
        <span style={{ color: "var(--muted)", fontSize: "14px" }}>
          {step + 1} / {QUESTIONS.length}
        </span>
      </div>

      {step === 0 ? (
        <p
          style={{
            fontSize: "13px",
            color: "var(--muted)",
            lineHeight: 1.6,
            margin: "0 0 4px",
            padding: "12px 14px",
            background: "rgba(0,0,140,0.05)",
            borderRadius: "10px",
            border: "1px solid rgba(0,0,140,0.12)",
          }}
        >
          {t("evaluationIntro")}
        </p>
      ) : null}

      <p style={{ fontSize: "16px", fontWeight: 500, margin: "8px 0 20px" }}>{question.text}</p>

      {question.type === "likert" && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", fontSize: "13px", color: "var(--muted)" }}>
            <span>{question.low}</span>
            <span>{question.high}</span>
          </div>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
            {[1, 2, 3, 4, 5].map((val) => (
              <button
                key={val}
                onClick={() => setAnswer(val)}
                style={{
                  width: "52px",
                  height: "52px",
                  borderRadius: "50%",
                  border: "2px solid var(--ink)",
                  background: current === val ? "var(--ink)" : "transparent",
                  color: current === val ? "#fff" : "var(--ink)",
                  fontSize: "16px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {val}
              </button>
            ))}
          </div>
        </div>
      )}

      {question.type === "text" && (
        <textarea
          value={typeof current === "string" ? current : ""}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder={t("notesPlaceholder")}
          style={{
            width: "100%",
            minHeight: "120px",
            padding: "12px",
            borderRadius: "8px",
            border: "1px solid var(--border)",
            fontSize: "15px",
            resize: "vertical",
            boxSizing: "border-box",
          }}
        />
      )}

      <div style={{ display: "flex", gap: "12px", marginTop: "24px" }}>
        {step > 0 && (
          <button className="btn secondary" onClick={() => setStep((s) => s - 1)}>
            {t("back")}
          </button>
        )}
        {!isLast ? (
          <button
            className="btn"
            onClick={() => setStep((s) => s + 1)}
            disabled={current === null}
          >
            {t("next")}
          </button>
        ) : (
          <button className="btn" onClick={handleSubmit}>
            {t("submit")}
          </button>
        )}
      </div>
    </div>
  );
}
