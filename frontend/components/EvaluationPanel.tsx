"use client";

import { useState } from "react";

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

const QUESTIONS: Question[] = [
  { type: "likert", text: "Ich bin mit dem Feedback zufrieden.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Ich empfinde das Feedback als fair.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Ich halte das Feedback für gerechtfertigt.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Ich empfinde das Feedback als nützlich.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Ich empfinde das Feedback als hilfreich.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Das Feedback unterstützt mich stark.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Ich akzeptiere das Feedback.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Ich zweifle das Feedback an.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Ich weise das Feedback zurück.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Ich bin bereit, meine Leistung zu verbessern.", low: "trifft nicht zu", high: "trifft zu" },
  { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … zufrieden.", low: "Gar nicht", high: "Sehr" },
  { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … selbstsicher.", low: "Gar nicht", high: "Sehr" },
  { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … erfolgreich.", low: "Gar nicht", high: "Sehr" },
  { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … beleidigt.", low: "Gar nicht", high: "Sehr" },
  { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … verärgert.", low: "Gar nicht", high: "Sehr" },
  { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … frustriert.", low: "Gar nicht", high: "Sehr" },
  { type: "text", text: "Haben Sie weitere Anmerkungen?" },
];

interface EvaluationPanelProps {
  onComplete?: () => void;
}

export default function EvaluationPanel({ onComplete }: EvaluationPanelProps) {
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
        <h2 style={{ fontFamily: "var(--font-fraunces)", marginTop: 0 }}>Vielen Dank!</h2>
        <p style={{ color: "var(--muted)" }}>Ihre Antworten wurden gespeichert.</p>
        <button
          className="btn secondary"
          style={{ marginTop: "16px" }}
          onClick={() => { setStep(0); setAnswers(Array(QUESTIONS.length).fill(null)); setSubmitted(false); }}
        >
          Neu starten
        </button>
      </div>
    );
  }

  return (
    <div className="panel fade-in stack">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontFamily: "var(--font-fraunces)", margin: 0 }}>Evaluation</h2>
        <span style={{ color: "var(--muted)", fontSize: "14px" }}>
          {step + 1} / {QUESTIONS.length}
        </span>
      </div>

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
          placeholder="Ihre Anmerkungen..."
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
            Zurück
          </button>
        )}
        {!isLast ? (
          <button
            className="btn"
            onClick={() => setStep((s) => s + 1)}
            disabled={current === null}
          >
            Weiter
          </button>
        ) : (
          <button className="btn" onClick={handleSubmit}>
            Absenden
          </button>
        )}
      </div>
    </div>
  );
}
