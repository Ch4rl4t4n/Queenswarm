import { redirect } from "next/navigation";
import nextDynamic from "next/dynamic";
import Link from "next/link";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { PluginsUserUploader } from "@/components/hive/plugins-user-uploader";
import { ToolsMarketplacePanel } from "@/components/connectors/tools-marketplace-panel";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { hubFallbackTarget } from "@/lib/hive-navigation-mode";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";

interface ConnectorsEnvelope {
  items: DynamicConnectorPayload[];
}

interface ExternalProjectRow {
  id: string;
  slug: string;
  display_name: string;
  project_kind: string;
  is_active: boolean;
}

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
  installed: PluginInstalled[];
  user?: PluginInstalled[];
}

const ConnectorsConsole = nextDynamic(async () => {
  const mod = await import("@/components/connectors/connectors-console");
  return { default: mod.ConnectorsConsole };
});

const ExternalProjectsConsole = nextDynamic(async () => {
  const mod = await import("@/components/external-projects/external-projects-console");
  return { default: mod.ExternalProjectsConsole };
});

export const dynamic = "force-dynamic";

type IntegrationCardStatus = "connected" | "error" | "rate_limited";
type IntegrationCard = {
  id: string;
  title: string;
  subtitle: string;
  status: IntegrationCardStatus;
  actionHref: string;
  actionLabel: string;
};

function statusTone(status: IntegrationCardStatus): string {
  if (status === "connected") return "text-[#00FF88] border-[#00FF88]/40 bg-[#00FF88]/10";
  if (status === "rate_limited") return "text-[#FFB800] border-[#FFB800]/40 bg-[#FFB800]/10";
  return "text-[#FF3366] border-[#FF3366]/40 bg-[#FF3366]/10";
}

function pluginStatus(plugin: PluginInstalled): IntegrationCardStatus {
  const normalized = String(plugin.status ?? "").toLowerCase();
  if (normalized.includes("rate")) return "rate_limited";
  if (normalized.includes("error") || normalized.includes("fail")) return "error";
  if (normalized === "active" || plugin.enabled) return "connected";
  return "error";
}

export default async function IntegrationsPage(): Promise<JSX.Element> {
  if (!PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect(hubFallbackTarget("integrations"));
  }

  const [connectorsBody, externalRows, pluginsPack] = await Promise.all([
    hiveServerRawJson<ConnectorsEnvelope>("/connectors/dynamic"),
    hiveServerRawJson<ExternalProjectRow[]>("/external/projects"),
    hiveServerRawJson<PluginsPayload>("/plugins"),
  ]);

  const connectorRows = connectorsBody?.items ?? [];
  const externalProjects = externalRows ?? [];
  const pluginRows = pluginsPack?.installed ?? [];

  const activeCards: IntegrationCard[] = [
    ...connectorRows.map((conn) => ({
      id: `connector-${conn.id}`,
      title: conn.display_name,
      subtitle: `${conn.slug} · ${conn.auth_type}`,
      status: conn.is_active ? ("connected" as const) : ("error" as const),
      actionHref: "/integrations#hub",
      actionLabel: "Test connection",
    })),
    ...externalProjects.map((project) => ({
      id: `external-${project.id}`,
      title: project.display_name,
      subtitle: `${project.slug} · ${project.project_kind}`,
      status: project.is_active ? ("connected" as const) : ("error" as const),
      actionHref: "/integrations#external",
      actionLabel: "Open metrics",
    })),
    ...pluginRows.map((plugin) => ({
      id: `plugin-${plugin.id}`,
      title: plugin.title ?? plugin.id,
      subtitle: `v${plugin.version ?? "?"} · ${plugin.status ?? "n/a"}`,
      status: pluginStatus(plugin),
      actionHref: "/integrations#plugins",
      actionLabel: "Open catalog",
    })),
  ];

  return (
    <div className="scroll-smooth space-y-8">
      <HivePageHeader
        title="Integrations"
        subtitle="One integration control plane for connectors, external projects, and plugin catalog operations."
        info={{
          title: "Integrations",
          description: "Správa konektorov, pluginov a externých integrácií vrátane testovania pripojenia.",
          options: ["Connector Hub", "Marketplace", "External projects", "Plugin catalog"],
        }}
      />

      <section className="sticky top-2 z-10 space-y-3 rounded-2xl border border-cyan/20 bg-[#060b12]/90 p-4 backdrop-blur">
        <p className="text-xs uppercase tracking-[0.12em] text-cyan">Integration anchors</p>
        <div className="flex flex-wrap gap-2 text-xs">
          <a href="#active" className="rounded-full border border-cyan/30 px-2 py-1 text-cyan">#active</a>
          <a href="#ecosystem" className="rounded-full border border-cyan/30 px-2 py-1 text-cyan">#ecosystem</a>
          <a href="#hub" className="rounded-full border border-cyan/30 px-2 py-1 text-cyan">#hub</a>
          <a href="#external" className="rounded-full border border-cyan/30 px-2 py-1 text-cyan">#external</a>
          <a href="#plugins" className="rounded-full border border-cyan/30 px-2 py-1 text-cyan">#plugins</a>
        </div>
      </section>

      <section id="active" className="space-y-4 rounded-3xl border border-cyan/20 bg-[#070d17]/70 p-4 md:p-6">
        <header className="space-y-1">
          <h2 className="text-base font-semibold text-zinc-100 md:text-lg">Active Integrations</h2>
          <p className="text-xs text-zinc-400 md:text-sm">
            Unified health snapshot across connector hub, external bridges, and plugin lattice.
          </p>
        </header>
        {!activeCards.length ? (
          <p className="rounded-2xl border border-zinc-800 bg-black/20 p-4 text-sm text-zinc-400">
            No integrations found yet. Provision a connector in the hub below to start.
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {activeCards.map((card) => (
              <article key={card.id} className="rounded-2xl border border-zinc-800 bg-black/25 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-zinc-100">{card.title}</p>
                    <p className="mt-1 text-xs text-zinc-500">{card.subtitle}</p>
                  </div>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] ${statusTone(card.status)}`}>
                    {card.status}
                  </span>
                </div>
                <a href={card.actionHref} className="qs-btn qs-btn--ghost qs-btn--sm mt-3 inline-flex">
                  {card.actionLabel}
                </a>
              </article>
            ))}
          </div>
        )}
      </section>

      <section id="ecosystem" className="space-y-4 rounded-3xl border border-[#FFB800]/20 bg-[#100d07]/45 p-4 md:p-6">
        <header className="space-y-1">
          <h2 className="text-base font-semibold text-zinc-100 md:text-lg">Ecosystem Orchestration</h2>
          <p className="text-xs text-zinc-400 md:text-sm">
            Browser automation, voice control, and marketplace tools run as one operator loop: discover → execute → supervise.
          </p>
        </header>
        <div className="grid gap-3 md:grid-cols-3">
          <article className="rounded-2xl border border-zinc-800 bg-black/30 p-4">
            <p className="text-sm font-semibold text-zinc-100">Browser Harness</p>
            <p className="mt-1 text-xs text-zinc-500">Live browser sessions with approval guardrails in supervisor control-plane.</p>
            <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm mt-3 inline-flex">Open in Agents</Link>
          </article>
          <article className="rounded-2xl border border-zinc-800 bg-black/30 p-4">
            <p className="text-sm font-semibold text-zinc-100">Voice + Multimodal</p>
            <p className="mt-1 text-xs text-zinc-500">Voice-to-text command capture, live transcript, and TTS response playback.</p>
            <Link href="/ballroom" className="qs-btn qs-btn--ghost qs-btn--sm mt-3 inline-flex">Open Ballroom</Link>
          </article>
          <article className="rounded-2xl border border-zinc-800 bg-black/30 p-4">
            <p className="text-sm font-semibold text-zinc-100">Advanced Tools Marketplace</p>
            <p className="mt-1 text-xs text-zinc-500">Install new API tools one-click, then expose them to supervisor lanes dynamically.</p>
            <a href="#hub" className="qs-btn qs-btn--ghost qs-btn--sm mt-3 inline-flex">Install from Hub</a>
          </article>
        </div>
      </section>

      <section id="hub" className="space-y-4 rounded-3xl border border-zinc-800/80 bg-[#070b13]/70 p-4 md:p-6">
        <header className="space-y-1">
          <h2 className="text-base font-semibold text-zinc-100 md:text-lg">Dynamic Connector Hub</h2>
          <p className="text-xs text-zinc-400 md:text-sm">
            OAuth consent rail, connector provisioning, vault sync, and connection testing in one place.
          </p>
        </header>
        <ToolsMarketplacePanel />
        <ConnectorsConsole />
      </section>

      <section id="external" className="space-y-4 rounded-3xl border border-zinc-800/80 bg-[#070b13]/70 p-4 md:p-6">
        <header className="space-y-1">
          <h2 className="text-base font-semibold text-zinc-100 md:text-lg">External Projects</h2>
          <p className="text-xs text-zinc-400 md:text-sm">
            External project registry, API key issuance, and live success/latency metrics.
          </p>
        </header>
        <ExternalProjectsConsole />
      </section>

      <section id="plugins" className="space-y-4 rounded-3xl border border-zinc-800/80 bg-[#070b13]/70 p-4 md:p-6">
        <header className="space-y-1">
          <h2 className="text-base font-semibold text-zinc-100 md:text-lg">Plugin Catalog</h2>
          <p className="text-xs text-zinc-400 md:text-sm">
            Built-in modules and operator uploads with quick status inspection.
          </p>
        </header>
        {!pluginsPack ? (
          <p className="rounded-2xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger">
            Plugin catalog unavailable.
          </p>
        ) : (
          <>
            <div className="grid gap-3 md:grid-cols-2">
              {pluginRows.map((plug) => (
                <article key={plug.id} className="rounded-2xl border border-zinc-800 bg-black/25 p-4">
                  <p className="text-sm font-semibold text-zinc-100">{plug.title ?? plug.id}</p>
                  <p className="mt-1 text-xs text-zinc-500">{plug.description ?? "Awaiting operator notes."}</p>
                  <p className="mt-2 text-[11px] text-zinc-400">
                    v{plug.version ?? "?"} · {plug.status ?? "n/a"}
                  </p>
                </article>
              ))}
              {!pluginRows.length ? (
                <p className="rounded-xl border border-zinc-800 bg-black/20 p-3 text-sm text-zinc-500">No plugin rows present.</p>
              ) : null}
            </div>
            <PluginsUserUploader />
          </>
        )}
      </section>
    </div>
  );
}
