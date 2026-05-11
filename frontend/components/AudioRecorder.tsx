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
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
        <button className="btn" onClick={startRecording} disabled={isRecording}>
          Aufnahme starten
        </button>
        <button className="btn secondary" onClick={stopRecording} disabled={!isRecording}>
          Stop
        </button>
      </div>
      {audioUrl ? (
        <audio controls src={audioUrl} style={{ width: "100%" }} />
      ) : (
        <p style={{ color: "var(--muted)" }}>Noch keine Aufnahme.</p>
      )}
    </div>
  );
}
