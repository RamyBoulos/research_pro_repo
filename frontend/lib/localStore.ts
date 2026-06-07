import fs from "node:fs/promises";
import path from "node:path";
import type { EvaluationLanguageBundle, ResolvedEvaluationResult } from "@/types/evaluation";

export interface VideoRecord {
  id: string;
  title: string;
  order_index: number;
  category: string;
  storage_key: string;
}

export interface UserRecord {
  id: string;
  name: string;
  access_code: string;
  created_at: string;
}

export interface SubmissionRecord {
  id: string;
  user_id: string;
  video_id: string;
  status: "uploaded" | "processing" | "done" | "error";
  transcript?: string | null;
  evaluation?: ResolvedEvaluationResult | null;
  evaluations?: EvaluationLanguageBundle | null;
  error_message?: string | null;
  audio_path: string;
  created_at: string;
}

const dataDir = path.join(process.cwd(), "data");
const videosFile = path.join(dataDir, "videos.json");
const usersFile = path.join(dataDir, "users.json");
const submissionsFile = path.join(dataDir, "submissions.json");
const audioDir = path.join(dataDir, "audio");

async function ensureDataDirs() {
  await fs.mkdir(audioDir, { recursive: true });
  await fs.mkdir(dataDir, { recursive: true });
}

async function readJsonFile<T>(filePath: string, fallback: T): Promise<T> {
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

async function writeJsonFile<T>(filePath: string, data: T) {
  await fs.writeFile(filePath, JSON.stringify(data, null, 2), "utf-8");
}

export async function getVideos(): Promise<VideoRecord[]> {
  await ensureDataDirs();
  const videos = await readJsonFile<VideoRecord[]>(videosFile, []);
  return videos.sort((a, b) => a.order_index - b.order_index);
}

export async function getUsers(): Promise<UserRecord[]> {
  await ensureDataDirs();
  return readJsonFile<UserRecord[]>(usersFile, []);
}

export async function findUserByAccessCode(accessCode: string) {
  const users = await getUsers();
  return users.find((user) => user.access_code === accessCode) ?? null;
}

export async function getSubmission(id: string): Promise<SubmissionRecord | null> {
  await ensureDataDirs();
  const submissions = await readJsonFile<SubmissionRecord[]>(submissionsFile, []);
  return submissions.find((item) => item.id === id) ?? null;
}

export async function createSubmission(videoId: string, userId: string, audioBuffer: Buffer) {
  await ensureDataDirs();
  const id = crypto.randomUUID();
  const audioPath = path.join(audioDir, `${id}.webm`);
  await fs.writeFile(audioPath, audioBuffer);

  const submissions = await readJsonFile<SubmissionRecord[]>(submissionsFile, []);
  const record: SubmissionRecord = {
    id,
    user_id: userId,
    video_id: videoId,
    status: "uploaded",
    audio_path: audioPath,
    created_at: new Date().toISOString()
  };
  submissions.push(record);
  await writeJsonFile(submissionsFile, submissions);
  return record;
}

export async function updateSubmission(id: string, updates: Partial<SubmissionRecord>) {
  await ensureDataDirs();
  const submissions = await readJsonFile<SubmissionRecord[]>(submissionsFile, []);
  const index = submissions.findIndex((item) => item.id === id);
  if (index === -1) {
    return null;
  }
  submissions[index] = { ...submissions[index], ...updates };
  await writeJsonFile(submissionsFile, submissions);
  return submissions[index];
}

export async function readAudioBuffer(audioPath: string) {
  return fs.readFile(audioPath);
}
