import { NextResponse } from "next/server";
import { getSubmission, readAudioBuffer, updateSubmission } from "@/lib/localStore";
import { getSessionToken } from "@/lib/session";
import { getUserForSession } from "@/lib/auth";
import type { ResolvedEvaluationResult, TranscriptionResponse } from "@/types/evaluation";

const FASTAPI_BASE_URL = (process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const DEFAULT_OUTPUT_LANGUAGE = "de";

async function transcribeWithBackend(audioBuffer: Buffer): Promise<TranscriptionResponse> {
  const formData = new FormData();
  formData.append("audio", new Blob([audioBuffer], { type: "audio/webm" }), "recording.webm");

  const response = await fetch(`${FASTAPI_BASE_URL}/api/transcribe`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw new Error(`Backend transcription failed: ${response.status}`);
  }

  return response.json() as Promise<TranscriptionResponse>;
}

async function evaluateWithBackend(
  transcript: string,
  durationSeconds: number
): Promise<ResolvedEvaluationResult> {
  const response = await fetch(`${FASTAPI_BASE_URL}/api/evaluate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      transcript,
      duration_seconds: durationSeconds,
      output_language: DEFAULT_OUTPUT_LANGUAGE
    })
  });

  if (!response.ok) {
    throw new Error(`Backend evaluation failed: ${response.status}`);
  }

  return response.json() as Promise<ResolvedEvaluationResult>;
}

interface Params {
  params: { id: string };
}

export async function POST(_: Request, { params }: Params) {
  const user = await getUserForSession(await getSessionToken());
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const submission = await getSubmission(params.id);
  if (!submission || submission.user_id !== user.id) {
    return NextResponse.json({ error: "Submission not found" }, { status: 404 });
  }

  if (submission.status === "done") {
    return NextResponse.json({ status: "done" });
  }

  await updateSubmission(submission.id, { status: "processing", error_message: null });

  try {
    const audioBuffer = await readAudioBuffer(submission.audio_path);
    const { transcript, duration_seconds } = await transcribeWithBackend(audioBuffer);
    const evaluation = await evaluateWithBackend(transcript, duration_seconds);

    await updateSubmission(submission.id, {
      status: "done",
      transcript,
      evaluation,
      feedback: null,
      error_message: null
    });

    return NextResponse.json({ status: "done" });
  } catch (err: any) {
    console.error("Submission processing failed", {
      submissionId: submission.id,
      error: err?.message || err
    });
    if (err?.name === "AbortError") {
      return NextResponse.json({ status: "processing" }, { status: 202 });
    }

    await updateSubmission(submission.id, {
      status: "error",
      error_message: "Processing failed"
    });

    return NextResponse.json({ error: "Processing failed" }, { status: 500 });
  }
}
