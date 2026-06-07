"use client";

import { useEffect, useRef, useState } from "react";
import { useLanguage } from "@/lib/LanguageProvider";

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

  const { t } = useLanguage();

  const startRecording = async () => {
    onError(null);
    onRecordingReady(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      onError(t("browserNoAudio"));
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
      recorder.onerror = () => {
        stream.getTracks().forEach((track) => track.stop());
        setIsRecording(false);
        onError(t("recordingFailed"));
        onRecordingReady(null);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        setIsRecording(false);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (blob.size < 8000) {
          onError(t("recordingTooShort"));
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
    } catch (error) {
      setIsRecording(false);
      const message = error instanceof DOMException && error.name === "NotAllowedError"
        ? t("microphoneDenied")
        : t("recordingFailed");
      onError(message);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
  };

  return (
    <div className="stack">
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
        <button className="btn" onClick={startRecording} disabled={isRecording}>
          {t("startRecording")}
        </button>
        <button className="btn secondary" onClick={stopRecording} disabled={!isRecording}>
          {t("stopRecording")}
        </button>
        {isRecording ? (
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                background: "#c0392b",
                display: "inline-block",
                animation: "pulse 1.2s ease-in-out infinite",
              }}
            />
            <span style={{ fontSize: "14px", color: "#c0392b", fontWeight: 600 }}>
              {t("recordingInProgress")}
            </span>
          </div>
        ) : null}
      </div>
      {audioUrl ? (
        <audio controls src={audioUrl} style={{ width: "100%" }} />
      ) : (
        <p style={{ color: "var(--muted)" }}>{t("noRecording")}</p>
      )}
      <p style={{ fontSize: "12px", color: "var(--muted)", margin: 0 }}>
        {t("recordingPrivacyNotice")}
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
