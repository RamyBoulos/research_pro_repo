"use client";

import { useLanguage } from "@/lib/LanguageProvider";

interface VideoPlayerProps {
  url: string | null;
}

export default function VideoPlayer({ url }: VideoPlayerProps) {
  const { t } = useLanguage();

  if (!url) {
    return (
      <div
        style={{
          borderRadius: "16px",
          border: "1px dashed var(--border)",
          padding: "40px",
          textAlign: "center",
          color: "var(--muted)"
        }}
      >
        {t("videoLoading")}
      </div>
    );
  }

  return (
    <video
      key={url}
      controls
      style={{ width: "100%", borderRadius: "16px", border: "1px solid var(--border)" }}
    >
      <source src={url} />
      {t("videoUnsupported")}
    </video>
  );
}
