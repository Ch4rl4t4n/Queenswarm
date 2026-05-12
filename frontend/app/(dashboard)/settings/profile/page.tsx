import { hiveServerRawJson } from "@/lib/hive-server";
import type { DashboardOperatorMe } from "@/lib/hive-dashboard-session";

import { ProfileSettingsClient } from "./profile-settings-client";

export const dynamic = "force-dynamic";

export default async function SettingsProfilePage() {
  const me = await hiveServerRawJson<DashboardOperatorMe>("/auth/me");
  return <ProfileSettingsClient initialMe={me} />;
}
