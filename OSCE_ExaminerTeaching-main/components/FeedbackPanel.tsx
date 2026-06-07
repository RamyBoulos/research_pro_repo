"use client";

import { useState } from "react";

export interface FeedbackState {
  status: "idle" | "uploading" | "processing" | "done" | "error";
  transcript?: string | null;
  feedback?: string | null;
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
          <div style={{ whiteSpace: "pre-wrap" }}>{state.feedback}</div>
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
