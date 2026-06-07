import { NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";
import { getSessionToken } from "@/lib/session";
import { getUserForSession } from "@/lib/auth";
import { getVideos } from "@/lib/localStore";

const evaluationsDir = path.join(process.cwd(), "data", "evaluations");

export async function GET() {
  const user = await getUserForSession(getSessionToken());
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Check evaluation
  const evalPath = path.join(evaluationsDir, `${user.id}.json`);
  let evaluationDone = false;
  try {
    await fs.access(evalPath);
    evaluationDone = true;
  } catch {
    evaluationDone = false;
  }

  // Check which videos have a completed submission for this user
  const submissionsPath = path.join(process.cwd(), "data", "submissions.json");
  let submissions: { user_id: string; video_id: string; status: string }[] = [];
  try {
    const raw = await fs.readFile(submissionsPath, "utf-8");
    submissions = JSON.parse(raw);
  } catch {
    submissions = [];
  }

  const completedVideoIds = submissions
    .filter((s) => s.user_id === user.id && s.status === "done")
    .map((s) => s.video_id);

  const videos = await getVideos();
  const categories = [...new Set(videos.map((v) => v.category))];
  const allTasksDone =
    categories.length > 0 &&
    categories.every((cat) =>
      videos
        .filter((v) => v.category === cat)
        .some((v) => completedVideoIds.includes(v.id))
    );

  return NextResponse.json({ evaluationDone, completedVideoIds, allTasksDone });
}
