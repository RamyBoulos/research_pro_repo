"use client";

export interface VideoItem {
  id: string;
  title: string;
  order_index: number;
  category: string;
}

interface VideoSidebarProps {
  videos: VideoItem[];
  selectedId: string | null;
  completedIds: string[];
  onSelect: (id: string) => void;
}

export default function VideoSidebar({ videos, selectedId, completedIds, onSelect }: VideoSidebarProps) {
  const categories = [...new Set(videos.map((v) => v.category))];

  return (
    <div className="stack">
      {categories.length === 0 ? (
        <p style={{ color: "var(--muted)" }}>Keine Videos vorhanden.</p>
      ) : null}
      {categories.map((cat) => {
        const catVideos = videos.filter((v) => v.category === cat);
        const catDone = catVideos.some((v) => completedIds.includes(v.id));
        return (
          <div key={cat} className="stack" style={{ gap: "8px" }}>
            <h3 style={{ margin: 0, fontSize: "13px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {catDone ? "✓ " : ""}{cat}
            </h3>
            <div className="stack" style={{ gap: "6px" }}>
              {catVideos.map((video) => (
                <button
                  key={video.id}
                  onClick={() => onSelect(video.id)}
                  className="btn secondary"
                  style={{
                    textAlign: "left",
                    background: selectedId === video.id ? "var(--ink)" : "transparent",
                    color: selectedId === video.id ? "#fff" : "var(--ink)"
                  }}
                >
                  {completedIds.includes(video.id) ? "✓ " : ""}{video.title}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
