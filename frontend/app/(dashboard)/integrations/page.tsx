import { redirect } from "next/navigation";
import nextDynamic from "next/dynamic";

import {
  type ExternalProjectRow,
  type IntegrationsInitialPayload,
  type PluginInstalledRow,
} from "@/components/hive/integrations-page-client";
import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";
import { hubFallbackTarget } from "@/lib/hive-navigation-mode";
import { hiveServerRawJson } from "@/lib/hive-server";

interface ConnectorsEnvelope {
  items: DynamicConnectorPayload[];
}

interface PluginsPayload {
  reload_generation?: number;
  installed: PluginInstalledRow[];
}

export const dynamic = "force-dynamic";

const IntegrationsPageClient = nextDynamic(
  () => import("@/components/hive/integrations-page-client").then((mod) => ({ default: mod.IntegrationsPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

type IntegrationsSearchParams = Record<string, string | string[] | undefined>;

function readParam(params: IntegrationsSearchParams, key: string): string | undefined {
  const raw = params[key];
  if (typeof raw === "string") return raw;
  if (Array.isArray(raw)) return raw[0];
  return undefined;
}

export default async function IntegrationsPage({
  searchParams,
}: {
  searchParams: Promise<IntegrationsSearchParams>;
}): Promise<JSX.Element> {
  const sp = await searchParams;
  const initialTab = readParam(sp, "tab");
  const purchaseRaw = readParam(sp, "purchase");
  const purchaseOutcome =
    purchaseRaw === "success" || purchaseRaw === "cancel" ? purchaseRaw : null;
  const checkoutSessionId = readParam(sp, "session_id") ?? null;

  if (!PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect(hubFallbackTarget("integrations"));
  }

  const [connectorsBody, externalRows, pluginsPack] = await Promise.all([
    hiveServerRawJson<ConnectorsEnvelope>("/connectors/dynamic"),
    hiveServerRawJson<ExternalProjectRow[]>("/external/projects"),
    hiveServerRawJson<PluginsPayload>("/plugins"),
  ]);

  const initial: IntegrationsInitialPayload = {
    connectors: connectorsBody?.items ?? [],
    externalProjects: externalRows ?? [],
    plugins: pluginsPack?.installed ?? [],
    reloadGeneration: pluginsPack?.reload_generation,
  };

  return (
    <IntegrationsPageClient
      initial={initial}
      initialTab={initialTab as "active" | "hub" | "marketplace" | "skills" | "external" | "plugins" | undefined}
      purchaseOutcome={purchaseOutcome}
      checkoutSessionId={checkoutSessionId}
    />
  );
}
