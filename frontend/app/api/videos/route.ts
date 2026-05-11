import { NextResponse } from "next/server";
import { getVideos } from "@/lib/localStore";
import { getSessionToken } from "@/lib/session";
import { getUserForSession } from "@/lib/auth";

export async function GET() {
  const user = await getUserForSession(await getSessionToken());
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    const videos = await getVideos();
    return NextResponse.json({ videos });
  } catch {
    return NextResponse.json({ error: "Failed to load videos" }, { status: 500 });
  }
}
