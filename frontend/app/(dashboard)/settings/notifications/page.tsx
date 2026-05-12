import { hiveServerRawJson } from "@/lib/hive-server";
import type { DashboardOperatorMe } from "@/lib/hive-dashboard-session";

import { NotificationsSettingsClient } from "./notifications-settings-client";

export const dynamic = "force-dynamic";

export default async function SettingsNotificationsPage() {
  const me = await hiveServerRawJson<DashboardOperatorMe>("/auth/me");
  return <NotificationsSettingsClient initialMe={me} />;
}
