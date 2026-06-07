"use client";

import { useLanguage } from "@/lib/LanguageProvider";

export default function InfoPanel() {
  const { t } = useLanguage();

  return (
    <div className="panel fade-in stack">
      <h2 style={{ fontFamily: "var(--font-fraunces)", marginTop: 0 }}>
        {t("infoWelcomeTitle")}
      </h2>

      <p style={{ color: "var(--muted)", fontSize: "15px", lineHeight: 1.6 }}>
        {t("infoIntro")}
      </p>

      <div style={{
        background: "rgba(0, 0, 140, 0.07)",
        border: "1px solid rgba(0, 0, 140, 0.2)",
        borderRadius: "12px",
        padding: "14px 18px",
        fontSize: "14px",
        lineHeight: 1.6
      }}>
        <strong>{t("infoTaskHeading")}</strong> {t("infoTaskDescription")}
      </div>

      <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "4px 0" }} />

      <div className="stack" style={{ gap: "20px" }}>
        <Step number={1} title={t("infoStep1Title")}>{t("infoStep1")}</Step>
        <Step number={2} title={t("infoStep2Title")}>
          {t("infoStep2")}
          <ul style={{ marginTop: "8px", paddingLeft: "20px", lineHeight: 1.8 }}>
            <li>{t("infoStep2List1")}</li>
            <li>{t("infoStep2List2")}</li>
            <li>{t("infoStep2List3")}</li>
            <li>{t("infoStep2List4")}</li>
          </ul>
        </Step>
        <Step number={3} title={t("infoStep3Title")}>
          {t("infoStep3")}
          <br /><br />
          <strong>{t("infoPrivacyHeading")}</strong> {t("infoStep3Privacy")}
        </Step>
        <Step number={4} title={t("infoStep4Title")}>{t("infoStep4")}</Step>
        <Step number={5} title={t("infoStep5Title")}>{t("infoStep5")}</Step>
      </div>

      <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "4px 0" }} />

      <p style={{ fontSize: "13px", color: "var(--muted)", lineHeight: 1.6 }}>
        {t("infoFooter")}
      </p>
    </div>
  );
}

function Step({
  number,
  title,
  children,
}: {
  number: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", gap: "16px" }}>
      <div
        style={{
          flexShrink: 0,
          width: "32px",
          height: "32px",
          borderRadius: "50%",
          background: "var(--ink)",
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 700,
          fontSize: "14px",
          marginTop: "2px",
        }}
      >
        {number}
      </div>
      <div>
        <div style={{ fontWeight: 600, marginBottom: "6px" }}>{title}</div>
        <div style={{ fontSize: "14px", color: "var(--muted)", lineHeight: 1.6 }}>
          {children}
        </div>
      </div>
    </div>
  );
}
