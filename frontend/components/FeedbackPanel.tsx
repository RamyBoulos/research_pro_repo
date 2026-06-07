"use client";

import { useState } from "react";
import type { EvaluationLanguageBundle, ResolvedEvaluationResult } from "@/types/evaluation";
import CoachingPanel from "./CoachingPanel";
import { useLanguage } from "@/lib/LanguageProvider";

export interface FeedbackState {
  status: "idle" | "uploading" | "processing" | "done" | "error";
  transcript?: string | null;
  evaluation?: ResolvedEvaluationResult | null;
  evaluations?: EvaluationLanguageBundle | null;
  errorMessage?: string | null;
  info?: string | null;
}

interface FeedbackPanelProps {
  state: FeedbackState;
}

export default function FeedbackPanel({ state }: FeedbackPanelProps) {
  const [showTranscript, setShowTranscript] = useState(false);
  const { t } = useLanguage();

  return (
    <div className="panel fade-in stack">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>{t("evaluationHeader")}</h3>
        <span className="tag">
          {state.status === "idle" ? t("readyStatus") : state.status === "uploading" ? t("uploadingStatus") : state.status === "processing" ? t("processingStatus") : state.status}
        </span>
      </div>

      {state.status === "uploading" ? <p>{t("uploadingStatus")}</p> : null}
      {state.status === "processing" ? <p>{t("processingStatus")}</p> : null}
      {state.status === "error" ? (
        <p style={{ color: "#c0392b" }}>{state.errorMessage || t("errorDefault")}</p>
      ) : null}
      {state.status === "done" ? (
        <div className="stack">
          {state.evaluation ? <StructuredEvaluation evaluation={state.evaluation} /> : null}
          {state.evaluation && state.transcript ? (
            <CoachingPanel transcript={state.transcript} evaluation={state.evaluation} />
          ) : null}
          <button className="btn secondary" onClick={() => setShowTranscript((prev) => !prev)}>
            {showTranscript ? t("hideTranscript") : t("showTranscript")}
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
  const { t } = useLanguage();

  return (
    <div className="stack" style={{ gap: "16px" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "12px"
        }}
      >
        <MetricCard label={t("feedbackTotalScore")} value={`${evaluation.overall_score}/100`} />
        <MetricCard label={t("feedbackCriteriaMet")} value={`${evaluation.criteria_met}/${evaluation.total_criteria}`} />
        <MetricCard label={t("feedbackDuration")} value={`${Math.round(evaluation.duration_seconds)} s`} />
      </div>

      <div className="stack" style={{ gap: "8px" }}>
        <strong>{t("feedbackSummary")}</strong>
        <div style={{ whiteSpace: "pre-wrap" }}>{evaluation.summary}</div>
      </div>

      <div className="stack" style={{ gap: "12px" }}>
        <strong>{t("feedbackCriteria")}</strong>
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
        <strong>{t("feedbackKeySuggestion")}</strong>
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
