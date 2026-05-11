import { NextResponse } from "next/server";
import { createSubmission, getVideos } from "@/lib/localStore";
import { getSessionToken } from "@/lib/session";
import { getUserForSession } from "@/lib/auth";

export async function POST(request: Request) {
  const user = await getUserForSession(await getSessionToken());
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const formData = await request.formData();
  const file = formData.get("audio");
  const videoId = formData.get("videoId");

  if (!file || typeof videoId !== "string") {
    return NextResponse.json({ error: "Missing audio or videoId" }, { status: 400 });
  }

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "Invalid audio file" }, { status: 400 });
  }

  if (file.size < 8000) {
    return NextResponse.json({ error: "Audio too short" }, { status: 400 });
  }

  const videos = await getVideos();
  const video = videos.find((item) => item.id === videoId);
  if (!video) {
    return NextResponse.json({ error: "Video not found" }, { status: 404 });
  }

  const buffer = Buffer.from(await file.arrayBuffer());

  try {
    const submission = await createSubmission(videoId, user.id, buffer);
    return NextResponse.json({ submissionId: submission.id });
  } catch {
    return NextResponse.json({ error: "Failed to create submission" }, { status: 500 });
  }
}
