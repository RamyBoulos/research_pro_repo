import { NextResponse } from "next/server";
import { getSubmission, readAudioBuffer, updateSubmission } from "@/lib/localStore";
import { getSessionToken } from "@/lib/session";
import { getUserForSession } from "@/lib/auth";
import type {
  EvaluationLanguageBundle,
  EvaluationResult,
  Language,
  ResolvedCriterionResult,
  ResolvedEvaluationResult,
  TranscriptionResponse,
} from "@/types/evaluation";

const FASTAPI_BASE_URL = (process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const DEFAULT_OUTPUT_LANGUAGE = "de";
const SUPPORTED_LANGUAGES = new Set<Language>(["de", "en"]);

async function readErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json() as { detail?: string; error?: string };
    return data.detail || data.error || fallback;
  } catch {
    return fallback;
  }
}

async function transcribeWithBackend(audioBuffer: Buffer): Promise<TranscriptionResponse> {
  const formData = new FormData();
  const audioArrayBuffer = new Uint8Array(Array.from(audioBuffer)).buffer;
  formData.append("audio", new Blob([audioArrayBuffer], { type: "audio/webm" }), "recording.webm");

  const response = await fetch(`${FASTAPI_BASE_URL}/api/transcribe`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    const detail = await readErrorDetail(
      response,
      `Backend transcription failed: ${response.status}`
    );
    throw new Error(detail);
  }

  return response.json() as Promise<TranscriptionResponse>;
}

async function evaluateWithBackend(
  transcript: string,
  durationSeconds: number
): Promise<EvaluationLanguageBundle> {
  const response = await fetch(`${FASTAPI_BASE_URL}/api/evaluate/full`, {
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
    const detail = await readErrorDetail(
      response,
      `Backend evaluation failed: ${response.status}`
    );
    throw new Error(detail);
  }

  const evaluation = await response.json() as EvaluationResult;
  return {
    de: resolveEvaluationResult(evaluation, "de"),
    en: resolveEvaluationResult(evaluation, "en"),
  };
}

function resolveText(content: Record<Language, string>, language: Language) {
  return content[language] ?? content.en;
}

function resolveCriterionResult(
  criterion: EvaluationResult["criteria"][number],
  language: Language
): ResolvedCriterionResult {
  return {
    criterion_id: criterion.criterion_id,
    label: resolveText(criterion.label, language),
    score_percent: criterion.score_percent,
    suggestion: resolveText(criterion.suggestion, language),
    quote: criterion.quote ? resolveText(criterion.quote, language) : null,
  };
}

function resolveEvaluationResult(
  evaluation: EvaluationResult,
  language: Language
): ResolvedEvaluationResult {
  return {
    output_language: language,
    transcript: evaluation.transcript,
    duration_seconds: evaluation.duration_seconds,
    overall_score: evaluation.overall_score,
    summary: resolveText(evaluation.summary, language),
    criteria_met: evaluation.criteria_met,
    total_criteria: evaluation.total_criteria,
    criteria: evaluation.criteria.map((criterion) => resolveCriterionResult(criterion, language)),
    key_suggestion: resolveText(evaluation.key_suggestion, language),
  };
}

interface Params {
  params: Promise<{ id: string }> | { id: string };
}

export async function POST(request: Request, { params }: Params) {
  let outputLanguage: Language = DEFAULT_OUTPUT_LANGUAGE;
  try {
    const body = await request.json() as { output_language?: unknown };
    if (typeof body.output_language === "string" && SUPPORTED_LANGUAGES.has(body.output_language as Language)) {
      outputLanguage = body.output_language as Language;
    }
  } catch {
    outputLanguage = DEFAULT_OUTPUT_LANGUAGE;
  }

  const { id } = await params;
  const user = await getUserForSession(await getSessionToken());
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const submission = await getSubmission(id);
  if (!submission || submission.user_id !== user.id) {
    return NextResponse.json({ error: "Submission not found" }, { status: 404 });
  }

  if (submission.status === "done") {
    if (submission.evaluations?.[outputLanguage]) {
      await updateSubmission(submission.id, {
        evaluation: submission.evaluations[outputLanguage],
        error_message: null,
      });
    }
    return NextResponse.json({ status: "done" });
  }

  await updateSubmission(submission.id, { status: "processing", error_message: null });

  try {
    const audioBuffer = await readAudioBuffer(submission.audio_path);
    const { transcript, duration_seconds } = await transcribeWithBackend(audioBuffer);
    const evaluations = await evaluateWithBackend(transcript, duration_seconds);

    await updateSubmission(submission.id, {
      status: "done",
      transcript,
      evaluation: evaluations[outputLanguage],
      evaluations,
      error_message: null
    });

    return NextResponse.json({ status: "done" });
  } catch (err: any) {
    const message = err?.message || "Processing failed";
    console.error("Submission processing failed", {
      submissionId: submission.id,
      error: message
    });
    if (err?.name === "AbortError") {
      return NextResponse.json({ status: "processing" }, { status: 202 });
    }

    await updateSubmission(submission.id, {
      status: "error",
      error_message: message
    });

    return NextResponse.json({ error: message }, { status: 500 });
  }
}
