import { NextResponse } from "next/server";
import { findUserByAccessCode } from "@/lib/localStore";

export async function POST(request: Request) {
  const { accessCode } = await request.json();
  if (!accessCode || typeof accessCode !== "string") {
    return NextResponse.json({ error: "Zugangscode fehlt." }, { status: 400 });
  }
  const user = await findUserByAccessCode(accessCode);
  if (!user) {
    return NextResponse.json({ error: "Ungültiger Zugangscode." }, { status: 401 });
  }
  return NextResponse.json({ ok: true });
}
