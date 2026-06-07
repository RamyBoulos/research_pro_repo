import { cookies } from "next/headers";
import crypto from "node:crypto";

const SESSION_COOKIE = "osce_session";

export function createSessionToken() {
  return crypto.randomBytes(24).toString("hex");
}

export function setSessionCookie(token: string) {
  const cookieStore = cookies();
  cookieStore.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 12
  });
}

export function clearSessionCookie() {
  const cookieStore = cookies();
  cookieStore.set(SESSION_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    maxAge: 0
  });
}

export function getSessionToken() {
  return cookies().get(SESSION_COOKIE)?.value || null;
}
