"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/lib/LanguageProvider";

export default function LoginPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const [step, setStep] = useState<"code" | "name">("code");
  const [accessCode, setAccessCode] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCodeSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await fetch("/api/auth/validate-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accessCode })
      });
      if (!response.ok) {
        setError(t("loginInvalidCode"));
        return;
      }
      setStep("name");
    } catch {
      setError(t("loginUnexpectedError"));
    } finally {
      setLoading(false);
    }
  };

  const handleNameSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accessCode, firstName: firstName.trim(), lastName: lastName.trim() })
      });
      if (!response.ok) {
        setError(response.status === 401 ? t("loginInvalidCode") : t("loginFailed"));
        return;
      }
      router.push("/app");
    } catch {
      setError(t("loginUnexpectedLoginError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="stack" style={{ minHeight: "100vh", alignItems: "center", justifyContent: "center" }}>
      <div className="panel fade-in" style={{ width: "min(420px, 92vw)" }}>
        <div className="stack">
          <div>
            <p className="tag">OSCE Feedback</p>
            <h1 style={{ fontFamily: "var(--font-fraunces)", fontSize: "32px", margin: "12px 0 0" }}>
              {step === "code" ? t("loginAccessCode") : t("loginYourName")}
            </h1>
            <p style={{ color: "var(--muted)" }}>
              {step === "code"
                ? t("loginAccessCodePrompt")
                : t("loginNamePrompt")}
            </p>
          </div>

          {step === "code" ? (
            <form className="stack" onSubmit={handleCodeSubmit}>
              <label className="stack" style={{ gap: "6px" }}>
                <span>{t("loginAccessCode")}</span>
                <input
                  type="password"
                  required
                  value={accessCode}
                  onChange={(e) => setAccessCode(e.target.value)}
                  style={{ padding: "10px 12px", borderRadius: "12px", border: "1px solid var(--border)" }}
                />
              </label>
              {error ? <p style={{ color: "#c0392b" }}>{error}</p> : null}
              <button className="btn" type="submit" disabled={loading}>
                {loading ? t("loginChecking") : t("loginContinue")}
              </button>
            </form>
          ) : (
            <form className="stack" onSubmit={handleNameSubmit}>
              <label className="stack" style={{ gap: "6px" }}>
                <span>{t("loginFirstName")}</span>
                <input
                  type="text"
                  required
                  autoFocus
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  style={{ padding: "10px 12px", borderRadius: "12px", border: "1px solid var(--border)" }}
                />
              </label>
              <label className="stack" style={{ gap: "6px" }}>
                <span>{t("loginLastName")}</span>
                <input
                  type="text"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  style={{ padding: "10px 12px", borderRadius: "12px", border: "1px solid var(--border)" }}
                />
              </label>
              {error ? <p style={{ color: "#c0392b" }}>{error}</p> : null}
              <button className="btn" type="submit" disabled={loading}>
                {loading ? t("loginSigningIn") : t("loginSignIn")}
              </button>
              <button
                type="button"
                className="btn secondary"
                onClick={() => { setStep("code"); setError(null); }}
              >
                {t("loginBack")}
              </button>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
