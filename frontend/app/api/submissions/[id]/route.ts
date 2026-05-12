import { NextResponse } from "next/server";
import { getSubmission } from "@/lib/localStore";
import { getSessionToken } from "@/lib/session";
import { getUserForSession } from "@/lib/auth";

interface Params {
  params: Promise<{ id: string }> | { id: string };
}

export async function GET(_: Request, { params }: Params) {
  const { id } = await params;
  const user = await getUserForSession(await getSessionToken());
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const submission = await getSubmission(id);
  if (!submission || submission.user_id !== user.id) {
    return NextResponse.json({ error: "Submission not found" }, { status: 404 });
  }

  return NextResponse.json({ submission });
}
