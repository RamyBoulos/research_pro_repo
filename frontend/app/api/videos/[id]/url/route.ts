import { NextResponse } from "next/server";
import { getVideos } from "@/lib/localStore";
import { getSessionToken } from "@/lib/session";
import { getUserForSession } from "@/lib/auth";

interface Params {
  params: { id: string };
}

export async function GET(_: Request, { params }: Params) {
  const user = await getUserForSession(await getSessionToken());
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const videos = await getVideos();
  const video = videos.find((item) => item.id === params.id);

  if (!video) {
    return NextResponse.json({ error: "Video not found" }, { status: 404 });
  }

  const url = `/videos/${video.storage_key}`;
  return NextResponse.json({ url });
}
