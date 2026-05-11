import { redirect } from "next/navigation";
import AppShell from "@/components/AppShell";
import { getSessionToken } from "@/lib/session";
import { getUserForSession, sanitizeUser } from "@/lib/auth";

export default async function AppPage() {
  const token = await getSessionToken();
  const user = await getUserForSession(token);
  if (!user) {
    redirect("/login");
  }
  return <AppShell user={sanitizeUser(user)} />;
}
