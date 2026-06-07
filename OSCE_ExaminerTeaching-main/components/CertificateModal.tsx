"use client";


interface CertificateModalProps {
  name: string;
  onClose: () => void;
}

export default function CertificateModal({ name, onClose }: CertificateModalProps) {
  const handleDownload = () => {
    if (!name.trim()) return;

    const date = new Date().toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });

    const html = `<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <title>Teilnahmebescheinigung</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&family=Fraunces:ital,wght@0,400;0,700;1,400&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Space Grotesk', sans-serif;
      background: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 40px;
    }
    .cert {
      border: 3px solid #00008c;
      border-radius: 16px;
      padding: 64px 72px;
      max-width: 680px;
      width: 100%;
      text-align: center;
    }
    .label {
      font-size: 13px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #7d8894;
      margin-bottom: 32px;
    }
    h1 {
      font-family: 'Fraunces', serif;
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 40px;
      line-height: 1.2;
    }
    .body-text {
      font-size: 16px;
      line-height: 1.7;
      color: #00008c;
    }
    .name {
      font-family: 'Fraunces', serif;
      font-size: 26px;
      font-weight: 400;
      font-style: italic;
      border-bottom: 2px solid #00008c;
      display: inline-block;
      padding: 0 16px 6px;
      margin: 24px 0;
    }
    .divider {
      border: none;
      border-top: 1px solid rgba(31,27,22,0.15);
      margin: 40px 0;
    }
    .footer {
      font-size: 13px;
      color: #7d8894;
    }
    @media print {
      body { padding: 0; }
      .cert { border-radius: 0; max-width: 100%; }
    }
  </style>
</head>
<body>
  <div class="cert">
    <p class="label">Teilnahmebescheinigung</p>
    <h1>Prüferschulung</h1>
    <p class="body-text">Hiermit wird bestätigt, dass</p>
    <div class="name">${name.trim()}</div>
    <p class="body-text">
      erfolgreich an der <strong>Prüferschulung</strong> teilgenommen hat.
    </p>
    <hr class="divider" />
    <p class="footer">${date}</p>
  </div>
  <script>window.onload = () => window.print();</script>
</body>
</html>`;

    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    onClose();
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(31,27,22,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="panel stack"
        style={{ width: "100%", maxWidth: "420px", gap: "20px" }}
      >
        <h2 style={{ fontFamily: "var(--font-fraunces)", margin: 0 }}>
          Bescheinigung herunterladen
        </h2>
        <p style={{ color: "var(--muted)", margin: 0, fontSize: "14px" }}>
          Die Bescheinigung wird auf den Namen <strong>{name}</strong> ausgestellt.
        </p>
        <div style={{ display: "flex", gap: "12px" }}>
          <button className="btn secondary" onClick={onClose}>
            Abbrechen
          </button>
          <button className="btn" onClick={handleDownload} disabled={!name.trim()}>
            Herunterladen
          </button>
        </div>
      </div>
    </div>
  );
}
