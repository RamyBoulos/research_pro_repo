"use client";

import { useState } from "react";
import type { ResolvedEvaluationResult } from "@/types/evaluation";

export interface FeedbackState {
  status: "idle" | "uploading" | "processing" | "done" | "error";
  transcript?: string | null;
  evaluation?: ResolvedEvaluationResult | null;
  errorMessage?: string | null;
  info?: string | null;
}

interface FeedbackPanelProps {
  state: FeedbackState;
}

export default function FeedbackPanel({ state }: FeedbackPanelProps) {
  const [showTranscript, setShowTranscript] = useState(false);

  return (
    <div className="panel fade-in stack">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>Feedback</h3>
        <span className="tag">
          {state.status === "idle" ? "Bereit" : state.status}
        </span>
      </div>

      {state.status === "uploading" ? <p>Upload laeuft...</p> : null}
      {state.status === "processing" ? <p>Auswertung laeuft...</p> : null}
      {state.status === "error" ? (
        <p style={{ color: "#c0392b" }}>{state.errorMessage || "Fehler bei der Auswertung."}</p>
      ) : null}
      {state.status === "done" ? (
        <div className="stack">
          {state.evaluation ? <StructuredEvaluation evaluation={state.evaluation} /> : null}
          <button className="btn secondary" onClick={() => setShowTranscript((prev) => !prev)}>
            {showTranscript ? "Transcript ausblenden" : "Transcript anzeigen"}
          </button>
          {showTranscript ? (
            <div style={{ whiteSpace: "pre-wrap", color: "var(--muted)" }}>
              {state.transcript}
            </div>
          ) : null}
        </div>
      ) : null}
      {state.info ? <p style={{ color: "var(--muted)" }}>{state.info}</p> : null}
    </div>
  );
}

function StructuredEvaluation({ evaluation }: { evaluation: ResolvedEvaluationResult }) {
  return (
    <div className="stack" style={{ gap: "16px" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "12px"
        }}
      >
        <MetricCard label="Gesamtscore" value={`${evaluation.overall_score}/100`} />
        <MetricCard label="Kriterien erfüllt" value={`${evaluation.criteria_met}/${evaluation.total_criteria}`} />
        <MetricCard label="Dauer" value={`${Math.round(evaluation.duration_seconds)} s`} />
      </div>

      <div className="stack" style={{ gap: "8px" }}>
        <strong>Zusammenfassung</strong>
        <div style={{ whiteSpace: "pre-wrap" }}>{evaluation.summary}</div>
      </div>

      <div className="stack" style={{ gap: "12px" }}>
        <strong>Kriterien</strong>
        {evaluation.criteria.map((criterion) => (
          <div
            key={criterion.criterion_id}
            style={{
              border: "1px solid rgba(15, 23, 42, 0.12)",
              borderRadius: "14px",
              padding: "14px"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center" }}>
              <strong>{criterion.label}</strong>
              <span className="tag">{criterion.score_percent}%</span>
            </div>
            <div
              style={{
                marginTop: "10px",
                height: "8px",
                borderRadius: "999px",
                background: "rgba(15, 23, 42, 0.08)",
                overflow: "hidden"
              }}
            >
              <div
                style={{
                  width: `${criterion.score_percent}%`,
                  height: "100%",
                  background: "var(--accent)"
                }}
              />
            </div>
            <p style={{ marginTop: "10px", marginBottom: 0 }}>{criterion.suggestion}</p>
            {criterion.quote ? (
              <p style={{ marginTop: "8px", marginBottom: 0, color: "var(--muted)", fontStyle: "italic" }}>
                "{criterion.quote}"
              </p>
            ) : null}
          </div>
        ))}
      </div>

      <div className="stack" style={{ gap: "8px" }}>
        <strong>Wichtigste Empfehlung</strong>
        <div style={{ whiteSpace: "pre-wrap" }}>{evaluation.key_suggestion}</div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        border: "1px solid rgba(15, 23, 42, 0.12)",
        borderRadius: "14px",
        padding: "14px"
      }}
    >
      <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>{label}</div>
      <div style={{ fontSize: "1.2rem", fontWeight: 700, marginTop: "4px" }}>{value}</div>
    </div>
  );
}
