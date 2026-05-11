"use client";

export default function InfoPanel() {
  return (
    <div className="panel fade-in stack">
      <h2 style={{ fontFamily: "var(--font-fraunces)", marginTop: 0 }}>
        Willkommen zur Prüferschulung
      </h2>

      <p style={{ color: "var(--muted)", fontSize: "15px", lineHeight: 1.6 }}>
        Diese Schulung unterstützt Sie dabei, strukturiertes und qualitativ hochwertiges
        Feedback im Rahmen von OSCE-Prüfungen zu geben. Bitte lesen Sie die folgenden
        Hinweise sorgfältig durch, bevor Sie beginnen.
      </p>

      <div style={{
        background: "rgba(0, 0, 140, 0.07)",
        border: "1px solid rgba(0, 0, 140, 0.2)",
        borderRadius: "12px",
        padding: "14px 18px",
        fontSize: "14px",
        lineHeight: 1.6
      }}>
        <strong>Ihre Aufgabe:</strong> Bearbeiten Sie <strong>je ein Video</strong> aus den beiden Stationen:
        <ul style={{ marginTop: "8px", marginBottom: 0, paddingLeft: "20px", lineHeight: 1.8 }}>
          <li><strong>Kommunikationsstation</strong> – wählen Sie eines der verfügbaren Videos</li>
          <li><strong>Blutentnahme</strong> – wählen Sie eines der verfügbaren Videos</li>
        </ul>
        Für jedes dieser Videos nehmen Sie Ihr mündliches Feedback auf und starten die Auswertung.
        Erst wenn beide Stationen abgeschlossen und die Evaluation ausgefüllt sind, können Sie Ihre Teilnahmebescheinigung herunterladen.
      </div>

      <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "4px 0" }} />

      <div className="stack" style={{ gap: "20px" }}>
        <Step number={1} title="Video auswählen und anschauen">
          Wählen Sie im linken Menü <strong>je ein Video</strong> pro Station (Kommunikationsstation
          und Blutentnahme) aus und schauen Sie es vollständig an. Die Videos zeigen reale
          Prüfungssituationen aus dem OSCE-Format. Achten Sie dabei besonders auf das gezeigte
          Verhalten und die Interaktion zwischen Prüfer und Kandidat.
        </Step>

        <Step number={2} title="Mündliches Feedback aufnehmen">
          Nehmen Sie anschließend Ihr mündliches Feedback zu dem Video auf. Drücken Sie dazu
          auf „Aufnahme starten" und sprechen Sie Ihr Feedback frei ein. Orientieren Sie sich
          dabei an den Prinzipien für konstruktives Feedback:
          <ul style={{ marginTop: "8px", paddingLeft: "20px", lineHeight: 1.8 }}>
            <li>Ich-Botschaften verwenden</li>
            <li>Konkrete Beobachtungen benennen</li>
            <li>Beobachtung und Interpretation trennen</li>
            <li>Zukunftsorientierte Empfehlungen geben</li>
          </ul>
        </Step>

        <Step number={3} title="Auswertung starten">
          Klicken Sie auf „Auswertung starten", um Ihre Aufnahme zu verarbeiten. Das System
          analysiert Ihr Feedback anhand festgelegter Qualitätskriterien und gibt Ihnen eine
          detaillierte Rückmeldung zu Ihrer Feedbackqualität.
          <br /><br />
          <strong>Datenschutzhinweis:</strong> Ihre Audioaufnahmen werden ausschließlich auf
          lokalen Servern des EKFZ (Else Kröner Fresenius Zentrum für Digitale Gesundheit) mit
          lokal betriebenen Sprachmodellen verarbeitet. Eine Weitergabe an Dritte oder externe
          Dienste findet nicht statt.
        </Step>

        <Step number={4} title="Evaluation ausfüllen">
          Wechseln Sie nach der Auswertung zum Bereich „Evaluation" und beantworten Sie bitte
          alle Fragen zu Ihrer Erfahrung. Ihre Angaben sind anonym und werden ausschließlich
          für wissenschaftliche Zwecke verwendet.
        </Step>

        <Step number={5} title="Bescheinigung herunterladen">
          Nach Abschluss der Schulung können Sie sich über „Bescheinigung herunterladen" eine
          Teilnahmebescheinigung für die Prüferschulung ausstellen lassen.
        </Step>
      </div>

      <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "4px 0" }} />

      <p style={{ fontSize: "13px", color: "var(--muted)", lineHeight: 1.6 }}>
        Bei technischen Problemen oder Fragen wenden Sie sich bitte an die Studienleitung.
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
