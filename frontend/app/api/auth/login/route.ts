import { NextResponse } from "next/server";
import { createSessionForAccessCode } from "@/lib/auth";
import { setSessionCookie } from "@/lib/session";

export async function POST(request: Request) {
  const { accessCode, firstName, lastName } = await request.json();
  if (!accessCode || typeof accessCode !== "string") {
    return NextResponse.json({ error: "Zugangscode fehlt." }, { status: 400 });
  }
  if (!firstName || !lastName) {
    return NextResponse.json({ error: "Vor- und Nachname erforderlich." }, { status: 400 });
  }

  const name = `${firstName.trim()} ${lastName.trim()}`;
  const session = await createSessionForAccessCode(accessCode, name);
  if (!session) {
    return NextResponse.json({ error: "Ungültiger Zugangscode." }, { status: 401 });
  }

  await setSessionCookie(session.token);
  return NextResponse.json({ ok: true });
}
