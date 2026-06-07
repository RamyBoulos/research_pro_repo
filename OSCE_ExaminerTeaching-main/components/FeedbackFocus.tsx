"use client";

const FOCUS: Record<string, { section: string; points: string[] }[]> = {
  "Anamnese und Untersuchung": [
    {
      section: "Anamnese",
      points: [
        "Vollständigkeit der Symptome erfasst",
        "Gezielte Gesprächsführung, ggf. konkretisierendes Nachfragen",
        "Angemessene Zugewandtheit zur Patientin (Mimik, Gestik, Körperhaltung)",
      ],
    },
    {
      section: "Körperliche Untersuchung Abdomen",
      points: [
        "Strukturierter Ablauf der Untersuchung",
        "Untersuchungsschritte korrekt durchgeführt (Befunde können durch Untersuchung tatsächlich erhoben werden)",
        "Angemessene Kommunikation und Umgang mit der Patientin (Höflichkeit, Untersuchungsschritte erläutert, ggf. Ablenkungsmanöver/Beruhigung)",
      ],
    },
  ],
  "Blutentnahme": [
    {
      section: "Blutentnahme",
      points: [
        "Vorbereitung und Hygiene",
        "Technische Durchführung (strukturierter Ablauf)",
        "Kommunikation und Patientenumgang",
      ],
    },
  ],
};

interface FeedbackFocusProps {
  category: string;
}

export default function FeedbackFocus({ category }: FeedbackFocusProps) {
  const sections = FOCUS[category];
  if (!sections) return null;

  return (
    <div style={{
      background: "rgba(0, 0, 140, 0.04)",
      border: "1px solid rgba(0, 0, 140, 0.15)",
      borderRadius: "12px",
      padding: "16px 20px",
      fontSize: "14px",
      lineHeight: 1.6,
    }}>
      <div style={{ fontWeight: 700, marginBottom: "12px", color: "var(--brand)" }}>
        Feedbackschwerpunkte
      </div>
      <div style={{ display: "grid", gap: "12px" }}>
        {sections.map((s) => (
          <div key={s.section}>
            <div style={{ fontWeight: 600, marginBottom: "4px" }}>{s.section}:</div>
            <ul style={{ margin: 0, paddingLeft: "20px", color: "var(--muted)" }}>
              {s.points.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
