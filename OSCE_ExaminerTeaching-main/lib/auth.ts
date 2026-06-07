import fs from "node:fs/promises";
import path from "node:path";
import { createSessionToken } from "./session";
import { findUserByAccessCode, getUsers } from "./localStore";

interface SessionRecord {
  token: string;
  participant_id: string;
  name: string;
  created_at: string;
}

const dataDir = path.join(process.cwd(), "data");
const sessionsFile = path.join(dataDir, "sessions.json");

async function readSessions(): Promise<SessionRecord[]> {
  try {
    const raw = await fs.readFile(sessionsFile, "utf-8");
    return JSON.parse(raw) as SessionRecord[];
  } catch {
    return [];
  }
}

async function writeSessions(data: SessionRecord[]) {
  await fs.mkdir(dataDir, { recursive: true });
  await fs.writeFile(sessionsFile, JSON.stringify(data, null, 2), "utf-8");
}

export async function createSessionForAccessCode(accessCode: string, name: string) {
  const user = await findUserByAccessCode(accessCode);
  if (!user) {
    return null;
  }
  const token = createSessionToken();
  const participant_id = crypto.randomUUID();
  const sessions = await readSessions();
  sessions.push({ token, participant_id, name, created_at: new Date().toISOString() });
  await writeSessions(sessions);
  return { token, participant_id, name };
}

export async function getUserForSession(token: string | null) {
  if (!token) {
    return null;
  }
  const sessions = await readSessions();
  const session = sessions.find((item) => item.token === token);
  if (!session) {
    return null;
  }
  // Verify the access code still exists, but use session identity for id/name
  const users = await getUsers();
  if (users.length === 0) return null;
  return {
    id: session.participant_id,
    name: session.name,
    access_code: users[0].access_code,
  };
}

export function sanitizeUser(user: { id: string; name: string }) {
  return { id: user.id, name: user.name };
}
