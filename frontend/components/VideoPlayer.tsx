"use client";

interface VideoPlayerProps {
  url: string | null;
}

export default function VideoPlayer({ url }: VideoPlayerProps) {
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
        Video wird geladen...
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
      Dein Browser unterstuetzt dieses Video nicht.
    </video>
  );
}
