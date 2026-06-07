"use client";

import { useEffect, useRef, useState } from "react";

interface AudioRecorderProps {
  onRecordingReady: (blob: Blob | null) => void;
  onError: (message: string | null) => void;
}

export default function AudioRecorder({ onRecordingReady, onError }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  const startRecording = async () => {
    onError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      onError("Browser unterstuetzt keine Audioaufnahme.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (blob.size < 8000) {
          onError("Aufnahme zu kurz. Bitte erneut aufnehmen.");
          onRecordingReady(null);
          return;
        }
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        onRecordingReady(blob);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      onError("Mikrofon-Zugriff verweigert.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className="stack">
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
        <button className="btn" onClick={startRecording} disabled={isRecording}>
          Aufnahme starten
        </button>
        <button className="btn secondary" onClick={stopRecording} disabled={!isRecording}>
          Stop
        </button>
        {isRecording && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{
              width: "12px",
              height: "12px",
              borderRadius: "50%",
              background: "#c0392b",
              display: "inline-block",
              animation: "pulse 1.2s ease-in-out infinite",
            }} />
            <span style={{ fontSize: "14px", color: "#c0392b", fontWeight: 600 }}>
              Aufnahme läuft…
            </span>
          </div>
        )}
      </div>
      {audioUrl ? (
        <audio controls src={audioUrl} style={{ width: "100%" }} />
      ) : (
        <p style={{ color: "var(--muted)" }}>Noch keine Aufnahme.</p>
      )}
      <p style={{ fontSize: "12px", color: "var(--muted)", margin: 0 }}>
        Ihre Audioaufnahme wird ausschließlich zur Verarbeitung verwendet und nicht gespeichert.
      </p>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.3; transform: scale(0.7); }
        }
      `}</style>
    </div>
  );
}
