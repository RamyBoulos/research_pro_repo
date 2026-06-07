import { NextResponse } from "next/server";
import fs from "node:fs/promises";
import { evaluateTranscript, transcribeAudio } from "@/lib/openai";
import { getSubmission, readAudioBuffer, updateSubmission } from "@/lib/localStore";
import { getSessionToken } from "@/lib/session";
import { getUserForSession } from "@/lib/auth";

interface Params {
  params: { id: string };
}

export async function POST(_: Request, { params }: Params) {
  const user = await getUserForSession(getSessionToken());
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
    const transcript = await transcribeAudio(audioBuffer, "audio/webm");
    const feedback = await evaluateTranscript(transcript);

    await updateSubmission(submission.id, {
      status: "done",
      transcript,
      feedback,
      error_message: null
    });

    // Delete audio file after successful processing
    await fs.unlink(submission.audio_path).catch(() => {});

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
