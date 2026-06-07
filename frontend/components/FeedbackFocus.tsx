"use client";

import { useLanguage } from "@/lib/LanguageProvider";
import type { Language } from "@/types/evaluation";

type FocusSection = {
  section: Record<Language, string>;
  points: Record<Language, string>[];
};

const COMMUNICATION_FOCUS: FocusSection[] = [
  {
    section: {
      de: "Anamnese",
      en: "History taking",
    },
    points: [
      {
        de: "Vollständigkeit der Symptome erfasst",
        en: "Completeness of symptom assessment",
      },
      {
        de: "Gezielte Gesprächsführung, ggf. konkretisierendes Nachfragen",
        en: "Focused interview style, with clarifying follow-up questions where appropriate",
      },
      {
        de: "Angemessene Zugewandtheit zur Patientin (Mimik, Gestik, Körperhaltung)",
        en: "Appropriate attentiveness toward the patient (facial expression, gestures, posture)",
      },
    ],
  },
  {
    section: {
      de: "Körperliche Untersuchung Abdomen",
      en: "Physical abdominal examination",
    },
    points: [
      {
        de: "Strukturierter Ablauf der Untersuchung",
        en: "Structured examination sequence",
      },
      {
        de: "Untersuchungsschritte korrekt durchgeführt (Befunde können durch Untersuchung tatsächlich erhoben werden)",
        en: "Examination steps performed correctly so findings can actually be elicited",
      },
      {
        de: "Angemessene Kommunikation und Umgang mit der Patientin (Höflichkeit, Untersuchungsschritte erläutert, ggf. Ablenkungsmanöver/Beruhigung)",
        en: "Appropriate communication and patient handling (politeness, explaining examination steps, distraction or reassurance where appropriate)",
      },
    ],
  },
];

const FOCUS: Record<string, FocusSection[]> = {
  Kommunikationsstation: COMMUNICATION_FOCUS,
  "Anamnese und Untersuchung": COMMUNICATION_FOCUS,
  Blutentnahme: [
    {
      section: {
        de: "Blutentnahme",
        en: "Blood draw",
      },
      points: [
        {
          de: "Vorbereitung und Hygiene",
          en: "Preparation and hygiene",
        },
        {
          de: "Technische Durchführung (strukturierter Ablauf)",
          en: "Technical execution (structured sequence)",
        },
        {
          de: "Kommunikation und Patientenumgang",
          en: "Communication and patient handling",
        },
      ],
    },
  ],
};

interface FeedbackFocusProps {
  category: string;
}

export default function FeedbackFocus({ category }: FeedbackFocusProps) {
  const { language, t } = useLanguage();
  const sections = FOCUS[category];
  if (!sections) return null;

  return (
    <div
      style={{
        background: "rgba(0, 0, 140, 0.04)",
        border: "1px solid rgba(0, 0, 140, 0.15)",
        borderRadius: "12px",
        padding: "16px 20px",
        fontSize: "14px",
        lineHeight: 1.6,
        marginTop: "16px",
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: "12px", color: "var(--brand)" }}>
        {t("feedbackFocusTitle")}
      </div>
      <div style={{ display: "grid", gap: "12px" }}>
        {sections.map((section) => (
          <div key={section.section.de}>
            <div style={{ fontWeight: 600, marginBottom: "4px" }}>{section.section[language]}:</div>
            <ul style={{ margin: 0, paddingLeft: "20px", color: "var(--muted)" }}>
              {section.points.map((point) => (
                <li key={point.de}>{point[language]}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
