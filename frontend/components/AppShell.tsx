"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AudioRecorder from "./AudioRecorder";
import FeedbackPanel, { FeedbackState } from "./FeedbackPanel";
import VideoPlayer from "./VideoPlayer";
import VideoSidebar, { VideoItem } from "./VideoSidebar";
import EvaluationPanel from "./EvaluationPanel";
import CertificateModal from "./CertificateModal";
import InfoPanel from "./InfoPanel";
import { useLanguage } from "@/lib/LanguageProvider";

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 60000;

interface AppShellProps {
  user: { id: string; name: string };
}

export default function AppShell({ user }: AppShellProps) {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [feedback, setFeedback] = useState<FeedbackState>({ status: "idle" });
  const [currentSubmissionId, setCurrentSubmissionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"videos" | "evaluation" | "info">("info");
  const [showCertificate, setShowCertificate] = useState(false);
  const [completedVideoIds, setCompletedVideoIds] = useState<string[]>([]);
  const [evaluationDone, setEvaluationDone] = useState(false);
  const { language, setLanguage, t } = useLanguage();

  const selectedVideo = useMemo(
    () => videos.find((video) => video.id === selectedVideoId) || null,
    [videos, selectedVideoId]
  );

  const categories = [...new Set(videos.map((v) => v.category))];
  const allTasksDone =
    categories.length > 0 &&
    categories.every((cat) =>
      videos.filter((v) => v.category === cat).some((v) => completedVideoIds.includes(v.id))
    );
  const canDownloadCertificate = allTasksDone && evaluationDone;

  const loadStatus = useCallback(async () => {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();
    setCompletedVideoIds(data.completedVideoIds ?? []);
    setEvaluationDone(data.evaluationDone ?? false);
  }, []);

  const loadVideos = useCallback(async () => {
    const response = await fetch("/api/videos");
    if (!response.ok) {
      setError(t("videoLoadFailed"));
      return;
    }
    const data = await response.json();
    setVideos(data.videos || []);
    if (!selectedVideoId && data.videos?.length) {
      setSelectedVideoId(data.videos[0].id);
    }
  }, [selectedVideoId, t]);

  const loadVideoUrl = useCallback(async (videoId: string) => {
    const response = await fetch(`/api/videos/${videoId}/url`);
    if (!response.ok) {
      setError(t("videoUrlFailed"));
      return;
    }
    const data = await response.json();
    setVideoUrl(data.url);
  }, [t]);

  useEffect(() => {
    loadVideos();
    loadStatus();
  }, [loadVideos, loadStatus]);

  useEffect(() => {
    if (selectedVideoId) {
      loadVideoUrl(selectedVideoId);
    }
  }, [selectedVideoId, loadVideoUrl]);

  const pollSubmission = async (submissionId: string) => {
    const start = Date.now();
    while (Date.now() - start < POLL_TIMEOUT_MS) {
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      const response = await fetch(`/api/submissions/${submissionId}`);
      if (!response.ok) {
        setFeedback({ status: "error", errorMessage: t("statusLoadFailed") });
        return;
      }
      const data = await response.json();
      const submission = data.submission;
      if (submission.status === "done") {
        setCurrentSubmissionId(submission.id);
        setFeedback({
          status: "done",
          transcript: submission.transcript,
          evaluation: submission.evaluation,
          evaluations: submission.evaluations
        });
        loadStatus();
        return;
      }
      if (submission.status === "error") {
        setFeedback({
          status: "error",
          errorMessage: submission.error_message || t("processingFailed")
        });
        return;
      }
    }
    setFeedback({ status: "processing", info: t("processingFailed") });
  };

  const handleProcess = async () => {
    if (!audioBlob) {
      setError(t("audioRequired"));
      return;
    }
    if (!selectedVideoId) {
      setError(t("videoRequired"));
      return;
    }

    setError(null);
    setCurrentSubmissionId(null);
    setFeedback({ status: "uploading" });

    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");
    formData.append("videoId", selectedVideoId);

    const uploadResponse = await fetch("/api/submissions", {
      method: "POST",
      body: formData
    });

    if (!uploadResponse.ok) {
      const data = await uploadResponse.json();
      setFeedback({ status: "error", errorMessage: data.error || t("uploadFailed") });
      return;
    }

    const uploadData = await uploadResponse.json();
    const submissionId = uploadData.submissionId as string;
    setCurrentSubmissionId(submissionId);

    setFeedback({ status: "processing" });
    const processResponse = await fetch(`/api/submissions/${submissionId}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ output_language: language }),
    });

    if (processResponse.ok) {
      const data = await processResponse.json();
      if (data.status === "done" || data.status === "processing") {
        await pollSubmission(submissionId);
        return;
      }
    }

    if (processResponse.status === 202) {
      await pollSubmission(submissionId);
      return;
    }

    const errorData = await processResponse.json();
    setFeedback({ status: "error", errorMessage: errorData.error || t("processingFailed") });
  };

  useEffect(() => {
    if (
      feedback.status !== "done" ||
      !feedback.evaluation ||
      !feedback.evaluations ||
      feedback.evaluation.output_language === language
    ) {
      return;
    }

    const localizedEvaluation = feedback.evaluations[language];
    if (!localizedEvaluation) {
      return;
    }

    setFeedback((prev) => ({
      ...prev,
      status: "done",
      evaluation: localizedEvaluation,
      info: null,
    }));
  }, [feedback, language]);

  return (
    <>
      {showCertificate && <CertificateModal name={user.name} onClose={() => setShowCertificate(false)} />}
      <main className="app-shell">
        <aside className="panel stack fade-in">
          <div className="stack" style={{ gap: "8px" }}>
            <p className="tag">{t("loggedInAs")}</p>
            <div style={{ fontWeight: 600 }}>{user.name}</div>
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button
              className="btn secondary sidebar-language-toggle"
              onClick={() => setLanguage("de")}
              style={{
                borderColor: language === "de" ? "var(--ink)" : "transparent",
                color: language === "de" ? "var(--ink)" : "var(--muted)",
              }}
            >
              DE
            </button>
            <button
              className="btn secondary sidebar-language-toggle"
              onClick={() => setLanguage("en")}
              style={{
                borderColor: language === "en" ? "var(--ink)" : "transparent",
                color: language === "en" ? "var(--ink)" : "var(--muted)",
              }}
            >
              EN
            </button>
          </div>
          <button
            className="btn secondary sidebar-nav-button"
            onClick={() => setActiveTab("info")}
            style={{
              background: activeTab === "info" ? "var(--ink)" : "transparent",
              color: activeTab === "info" ? "#fff" : "var(--ink)"
            }}
          >
            {t("informationTab")}
          </button>
          <VideoSidebar
            videos={videos}
            selectedId={selectedVideoId}
            completedIds={completedVideoIds}
            onSelect={(id) => {
              setSelectedVideoId(id);
              setAudioBlob(null);
              setCurrentSubmissionId(null);
              setFeedback({ status: "idle" });
              setActiveTab("videos");
            }}
          />
          <button
            className="btn secondary sidebar-nav-button"
            onClick={() => setActiveTab("evaluation")}
            style={{
              background: activeTab === "evaluation" ? "var(--ink)" : "transparent",
              color: activeTab === "evaluation" ? "#fff" : "var(--ink)"
            }}
          >
            {t("evaluationTab")} {evaluationDone ? "✓" : ""}
          </button>
          <button
            className="btn secondary sidebar-nav-button"
            onClick={() => canDownloadCertificate && setShowCertificate(true)}
            disabled={!canDownloadCertificate}
            title={
              !canDownloadCertificate ? t("certificatePendingTooltip") : undefined
            }
          >
            {t("certificateDownload")}
          </button>
          <button className="btn secondary sidebar-nav-button" onClick={handleLogout}>
            {t("logout")}
          </button>
        </aside>
        <section className="stack">
          {activeTab === "info" ? (
            <InfoPanel />
          ) : activeTab === "evaluation" ? (
            <EvaluationPanel onComplete={() => { setEvaluationDone(true); loadStatus(); }} />
          ) : (
            <>
              <div className="panel fade-in">
                <h2 style={{ fontFamily: "var(--font-fraunces)", marginTop: 0 }}>
                  {selectedVideo?.title || t("selectVideoPlaceholder")}
                </h2>
                <VideoPlayer url={videoUrl} />
                <div style={{ marginTop: "20px" }} className="stack">
                  <AudioRecorder onRecordingReady={setAudioBlob} onError={setError} />
                  <button className="btn" onClick={handleProcess} disabled={feedback.status === "processing"}>
                    {t("startEvaluation")}
                  </button>
                  {error ? <p style={{ color: "#c0392b" }}>{error}</p> : null}
                </div>
              </div>
              <FeedbackPanel state={feedback} />
            </>
          )}
        </section>
      </main>
    </>
  );

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }
}
