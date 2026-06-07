import { NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";
import { getSessionToken } from "@/lib/session";
import { getUserForSession } from "@/lib/auth";

const evaluationsDir = path.join(process.cwd(), "data", "evaluations");

export async function POST(request: Request) {
  const user = await getUserForSession(getSessionToken());
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { answers } = body as { answers: (number | string | null)[] };

  if (!Array.isArray(answers)) {
    return NextResponse.json({ error: "Invalid answers" }, { status: 400 });
  }

  await fs.mkdir(evaluationsDir, { recursive: true });

  const filePath = path.join(evaluationsDir, `${user.id}.json`);
  const record = {
    participant_id: user.id,
    user_name: user.name,
    submitted_at: new Date().toISOString(),
    answers,
  };

  await fs.writeFile(filePath, JSON.stringify(record, null, 2), "utf-8");

  return NextResponse.json({ ok: true });
}
