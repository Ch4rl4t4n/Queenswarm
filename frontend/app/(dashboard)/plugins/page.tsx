import nextDynamic from "next/dynamic";
import { redirect } from "next/navigation";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { integrationsTabHref } from "@/lib/integrations-routes";
import { hiveServerRawJson } from "@/lib/hive-server";

const PluginsPageClient = nextDynamic(
  () => import("@/components/hive/plugins-page-client").then((mod) => ({ default: mod.PluginsPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

interface PluginInstalled {
  id: string;
  title?: string;
  enabled?: boolean;
  description?: string;
  version?: string;
  status?: string;
}

interface PluginsPayload {
  reload_generation?: number;
  builtin?: PluginInstalled[];
  installed: PluginInstalled[];
  user?: PluginInstalled[];
}

export default async function PluginsPhasePage() {
  if (PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect(integrationsTabHref("plugins"));
  }

  const pack = await hiveServerRawJson<PluginsPayload>("/plugins");

  return <PluginsPageClient pack={pack} />;
}
