"use client";

import Link from "next/link";
import { BookOpen, CheckCircle2, Circle, Github, Loader2, Mail } from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { OAuthConnectButton } from "@/components/connectors/oauth-connect-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import {
  applySoloBootstrap,
  fetchBootstrapChecklist,
  fetchOAuthProviders,
  fetchOAuthSetupGuide,
  installFreeConnectors,
  buildAllDepartmentSwarms,
  buildDepartmentSwarm,
  provisionSoloRouters,
  seedDefaultProfile,
  startFirstRunSession,
  type BootstrapChecklist,
  type OAuthProviderRow,
  type OAuthSetupGuide,
} from "@/lib/virtual-company-api";

const FREE_OAUTH_KEYS = ["notion_workspace", "google_gmail", "github_rest"] as const;

function VendorGlyph({ providerKey }: { providerKey: string }): JSX.Element {
  if (providerKey === "google_gmail") {
    return <Mail className="h-5 w-5" aria-hidden />;
  }
  if (providerKey === "github_rest") {
    return <Github className="h-5 w-5" aria-hidden />;
  }
  if (providerKey === "notion_workspace") {
    return <BookOpen className="h-5 w-5" aria-hidden />;
  }
  return <Mail className="h-5 w-5 opacity-60" aria-hidden />;
}

interface SetupStepProps {
  done: boolean;
  title: string;
  detail: string;
  children?: ReactNode;
  /** Keep action/status visible after the step is marked done. */
  keepChildrenVisible?: boolean;
}

function SetupStep({ done, title, detail, children, keepChildrenVisible = false }: SetupStepProps): JSX.Element {
  return (
    <li className="flex gap-3 rounded-xl border border-(--qs-border)/35 bg-black/30 px-3 py-3">
      {done ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#00FF88]" aria-hidden />
      ) : (
        <Circle className="mt-0.5 h-4 w-4 shrink-0 text-(--qs-text-3)" aria-hidden />
      )}
      <div className="min-w-0 flex-1 space-y-2">
        <div>
          <p className="text-sm font-semibold text-(--qs-text)">{title}</p>
          <p className="mt-0.5 text-xs text-(--qs-text-3)">{detail}</p>
        </div>
        {(!done || keepChildrenVisible) && children ? (
          <div className="flex flex-wrap gap-2">{children}</div>
        ) : null}
      </div>
    </li>
  );
}

export interface VirtualCompanySetupCardProps {
  /** Called after bootstrap actions so parent panels can refresh. */
  onChanged?: () => void;
}

/** Virtual Company free-first setup checklist for Execution Studio. */
export function VirtualCompanySetupCard({ onChanged }: VirtualCompanySetupCardProps): JSX.Element | null {
  const [checklist, setChecklist] = useState<BootstrapChecklist | null>(null);
  const [oauthGuide, setOauthGuide] = useState<OAuthSetupGuide | null>(null);
  const [oauthProviders, setOauthProviders] = useState<OAuthProviderRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const reload = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const [c, o, g] = await Promise.all([
        fetchBootstrapChecklist(),
        fetchOAuthProviders(),
        fetchOAuthSetupGuide(),
      ]);
      setChecklist(c);
      setOauthProviders(Array.isArray(o?.providers) ? o.providers : []);
      setOauthGuide(g);
    } catch {
      /* non-fatal — card hides when checklist unavailable */
      setChecklist(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const oauth = params.get("oauth");
    if (!oauth) {
      return;
    }
    if (oauth === "success") {
      const provider = params.get("provider");
      toast.success(
        provider
          ? `${provider} connected — connectors activated, super routers syncing`
          : "OAuth connected — checklist updated",
      );
      void reload().then(() => onChanged?.());
    } else {
      const reason = params.get("reason");
      toast.error(reason ? `OAuth failed: ${reason}` : "OAuth flow failed");
    }
    const url = new URL(window.location.href);
    url.searchParams.delete("oauth");
    url.searchParams.delete("provider");
    url.searchParams.delete("reason");
    window.history.replaceState({}, "", `${url.pathname}${url.search}`);
  }, [reload, onChanged]);

  const connectors = useMemo(() => checklist?.connectors ?? [], [checklist?.connectors]);
  const oauthProviderRows = useMemo(
    () => (Array.isArray(oauthProviders) ? oauthProviders : []),
    [oauthProviders],
  );

  const connectorsInstalled = useMemo(() => {
    if (connectors.length === 0) {
      return false;
    }
    return connectors.every((row) => row.installed);
  }, [connectors]);

  const oauthPending = useMemo(() => {
    if (connectors.length === 0) {
      return false;
    }
    return connectors.some((row) => row.installed && !row.installed_active);
  }, [connectors]);

  const connectorsConnected = checklist?.oauth_progress?.connected ?? 0;
  const connectorsTotal = checklist?.oauth_progress?.total ?? 3;
  const notionActive = connectors.some((row) => row.slug === "notion_workspace" && row.installed_active);
  const githubActive = connectors.some((row) => row.slug === "github_rest" && row.installed_active);
  const gmailActive = connectors.some((row) => row.slug === "gmail_workspace" && row.installed_active);
  const coreConnectorsReady = notionActive && githubActive;
  const gmailOnlyPending = coreConnectorsReady && !gmailActive;

  const soloRoutersReady = useMemo(() => {
    const sr = checklist?.super_routers;
    if (!sr) {
      return false;
    }
    return sr.provisioned >= sr.provisioned_total;
  }, [checklist?.super_routers]);

  const firstRunCount = checklist?.first_run?.completed_count ?? 0;
  const firstRunTotal = checklist?.first_run?.playbooks_total ?? 6;

  const allFirstRunsDone = checklist?.first_run?.all_department_first_runs_completed ?? false;

  const isFirstRunCompleted = (templateId: string): boolean =>
    checklist?.first_run?.completed_templates?.includes(templateId) ?? false;

  const copyRedirectUri = (): void => {
    const uri = oauthGuide?.redirect_uri;
    if (!uri) {
      return;
    }
    void navigator.clipboard.writeText(uri).then(() => {
      toast.success("Redirect URI copied");
    });
  };

  const copyEnvStub = (): void => {
    const uri = oauthGuide?.redirect_uri ?? "https://queenswarm.love/api/auth/callback/oauth";
    const stub = `# Paste into .env.prod.oauth on the hive host, then run:
# ./scripts/operator-oauth-redeploy.sh

OAUTH_NOTION_CLIENT_ID=
OAUTH_NOTION_CLIENT_SECRET=
OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=
OAUTH_GITHUB_CLIENT_ID=
OAUTH_GITHUB_CLIENT_SECRET=

# Redirect URI for all vendors: ${uri}
`;
    void navigator.clipboard.writeText(stub).then(() => {
      toast.success(".env.prod.oauth template copied");
    });
  };

  const copyTokensStub = (): void => {
    const stub = `# Paste into .env.prod.tokens on the hive host (gitignored), then run:
# APPLY=1 ./scripts/operator-vc-manual-tokens.sh
#
# Notion: https://www.notion.so/my-integrations → Internal Integration Secret
# GitHub: optional if gh auth login is active on the host

NOTION_INTEGRATION_TOKEN=
GITHUB_PAT=
`;
    void navigator.clipboard.writeText(stub).then(() => {
      toast.success(".env.prod.tokens template copied");
    });
  };

  const oauthConfigured = useMemo(() => {
    return oauthProviderRows
      .filter((row) => FREE_OAUTH_KEYS.includes(row.provider_key as (typeof FREE_OAUTH_KEYS)[number]))
      .every((row) => row.configured);
  }, [oauthProviderRows]);

  const marketingSwarmBuilt = useMemo(
    () => checklist?.swarms?.built_templates?.includes("marketing-ops") ?? false,
    [checklist?.swarms?.built_templates],
  );

  const allDeptsBuilt = useMemo(() => {
    const sw = checklist?.swarms;
    if (!sw) {
      return false;
    }
    return sw.departments_built >= sw.departments_total;
  }, [checklist?.swarms]);

  const oauthRows = useMemo(
    () =>
      oauthProviderRows.filter((row) =>
        FREE_OAUTH_KEYS.includes(row.provider_key as (typeof FREE_OAUTH_KEYS)[number]),
      ),
    [oauthProviderRows],
  );

  const oauthConnectRows = useMemo(() => {
    if (!connectorsInstalled) {
      return [];
    }
    if (gmailOnlyPending) {
      return oauthRows.filter((row) => row.provider_key === "google_gmail");
    }
    if (coreConnectorsReady) {
      return [];
    }
    return oauthRows;
  }, [connectorsInstalled, coreConnectorsReady, gmailOnlyPending, oauthRows]);

  const runAction = async (key: string, fn: () => Promise<unknown>, success: string): Promise<void> => {
    setBusyKey(key);
    try {
      await fn();
      await reload();
      onChanged?.();
      toast.success(success);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusyKey(null);
    }
  };

  if (loading && !checklist) {
    return (
      <V4Card className="flex items-center gap-2 p-4">
        <Loader2 className="h-4 w-4 animate-spin text-pollen" aria-hidden />
        <span className="text-xs text-(--qs-text-3)">Loading Virtual Company setup…</span>
      </V4Card>
    );
  }

  if (!checklist) {
    return null;
  }

  return (
    <V4Card glow className="shrink-0">
      <V4CardHeader
        title="Virtual Company setup"
        description="Free-first solo path: profile → routing → connectors → department swarms."
        actions={
          <V4Badge tone={checklist.simulate_path_complete ? "ok" : allFirstRunsDone && !oauthConfigured ? "warn" : "info"}>
            {checklist.readiness_score ?? 0}% ready
            {checklist.simulate_path_complete ? " · simulate complete" : null}
            {!checklist.simulate_path_complete && allFirstRunsDone ? " · 6/6 simulate" : !checklist.simulate_path_complete ? ` · ${firstRunCount}/${firstRunTotal} simulate` : null}
            {!oauthConfigured && checklist.oauth_progress
              ? ` · connectors ${connectorsConnected}/${connectorsTotal}`
              : null}
          </V4Badge>
        }
      />
      {allFirstRunsDone && checklist.simulate_path_complete ? (
        <div className="mb-3 rounded-xl border border-[#00FF88]/45 bg-[#00FF88]/10 px-3 py-2 text-xs text-[#00FF88]">
          Simulate path complete — department swarms, playbooks, and recipes are ready.
          Live Notion/Gmail connectors are optional until you need them.
        </div>
      ) : coreConnectorsReady ? (
        <div className="mb-3 rounded-xl border border-[#00FF88]/45 bg-[#00FF88]/10 px-3 py-2 text-xs text-[#00FF88]">
          Notion + GitHub active (manual tokens). Super routers 2/2.
          {gmailOnlyPending ? (
            <>
              {" "}
              <span className="text-(--qs-text-3)">Gmail is optional — add Google OAuth when you need Marketing/Sales email.</span>
            </>
          ) : null}
        </div>
      ) : allFirstRunsDone && !oauthConfigured ? (
        <div className="mb-3 rounded-xl border border-pollen/45 bg-pollen/10 px-3 py-2 text-xs text-pollen">
          All department simulate playbooks complete. OAuth is the last step to reach 100% readiness.
          {" "}
          <span className="text-(--qs-text-3)">
            Fast path: Notion internal token via{" "}
            <a
              href="https://www.notion.so/my-integrations"
              target="_blank"
              rel="noopener noreferrer"
              className="text-(--qs-cyan) underline-offset-2 hover:underline"
            >
              my-integrations
            </a>
            {" "}
            + <span className="font-mono">operator-vc-notion-onboard.sh</span>
          </span>
        </div>
      ) : null}
      {!oauthConfigured && !coreConnectorsReady ? (
        <div className="mb-3 space-y-2 rounded-xl border border-(--qs-magenta)/35 bg-(--qs-magenta)/10 px-3 py-2 text-xs text-(--qs-magenta)">
          <p>
            OAuth client IDs missing — edit <span className="font-mono">.env.prod.oauth</span> on the hive host. Register each vendor with redirect URI:{" "}
            <span className="font-mono text-(--qs-cyan)">{oauthGuide?.redirect_uri ?? "…"}</span>
            {oauthGuide?.redirect_uri ? (
              <button
                type="button"
                className="ml-2 text-(--qs-cyan) underline-offset-2 hover:underline"
                onClick={copyRedirectUri}
              >
                Copy
              </button>
            ) : null}
          </p>
          {oauthGuide?.vendors.length ? (
            <ul className="space-y-1">
              {oauthGuide.vendors.map((vendor) => (
                <li key={vendor.provider_key}>
                  {vendor.configured ? "✓" : "○"}{" "}
                  <a
                    href={vendor.console_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-(--qs-cyan) underline-offset-2 hover:underline"
                  >
                    {vendor.label}
                  </a>
                  {!vendor.configured ? (
                    <span className="text-(--qs-text-3)">
                      {" "}
                      · set {vendor.env_id} in .env.prod.oauth
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="flex flex-wrap gap-2 pt-1">
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={copyEnvStub}>
              Copy .env.prod.oauth template
            </button>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={copyTokensStub}>
              Copy .env.prod.tokens template
            </button>
            <a
              href="https://www.notion.so/my-integrations"
              target="_blank"
              rel="noopener noreferrer"
              className="qs-btn qs-btn--ghost qs-btn--sm"
            >
              Notion internal integration
            </a>
            <a
              href="https://console.cloud.google.com/apis/credentials"
              target="_blank"
              rel="noopener noreferrer"
              className="qs-btn qs-btn--ghost qs-btn--sm"
            >
              Google console
            </a>
            <a
              href="https://github.com/settings/developers"
              target="_blank"
              rel="noopener noreferrer"
              className="qs-btn qs-btn--ghost qs-btn--sm"
            >
              GitHub console
            </a>
          </div>
        </div>
      ) : null}
      <ol className="space-y-2">
        <SetupStep
          done={checklist.profile_complete}
          title="Operator profile"
          detail="Brand, industry, and goal flow into every department swarm HiveMind."
        >
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busyKey !== null}
            onClick={() => void runAction("seed", seedDefaultProfile, "Default profile seeded")}
          >
            {busyKey === "seed" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
            Seed solo defaults
          </button>
          <Link href="/swarms/new" className="qs-btn qs-btn--ghost qs-btn--sm">
            Edit profile
          </Link>
        </SetupStep>

        <SetupStep
          done={checklist.free_first_active}
          title="Free-first LLM routing"
          detail="Route to €0-capable models before paid fallbacks."
        >
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busyKey !== null}
            onClick={() => void runAction("routing", applySoloBootstrap, "Free-first routing enabled")}
          >
            {busyKey === "routing" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
            Enable free_first
          </button>
        </SetupStep>

        <SetupStep
          done={connectorsInstalled}
          title="Install connector templates"
          detail="Notion, Gmail, and GitHub rows in Dynamic Hub — no API keys required upfront."
        >
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busyKey !== null}
            onClick={() =>
              void runAction("install", installFreeConnectors, "Free connectors installed — complete OAuth next")
            }
          >
            {busyKey === "install" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
            Install Notion + Gmail + GitHub
          </button>
        </SetupStep>

        <SetupStep
          done={soloRoutersReady}
          title="Provision solo Super Tool Routers"
          detail="Routes mcp_invoke to Notion/Gmail/GitHub per department manager lane (auto-activates after OAuth)."
        >
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busyKey !== null}
            onClick={() =>
              void runAction("routers", provisionSoloRouters, "Solo super routers provisioned")
            }
          >
            {busyKey === "routers" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
            Provision VC routers
          </button>
        </SetupStep>

        <SetupStep
          done={connectorsInstalled && coreConnectorsReady}
          keepChildrenVisible
          title="Activate connectors"
          detail={
            connectorsInstalled
              ? coreConnectorsReady
                ? gmailOnlyPending
                  ? "Notion + GitHub active. Gmail optional for Marketing/Sales email."
                  : "All free connectors are active."
                : oauthPending
                  ? `${connectorsConnected}/${connectorsTotal} active — authorize or apply manual tokens.`
                  : "All free connectors are active."
              : "Install connector templates first, then connect each vendor."
          }
        >
          {connectorsInstalled ? (
            <div className="mb-2 flex flex-wrap gap-2 text-xs">
              <span className={notionActive ? "text-[#00FF88]" : "text-(--qs-text-3)"}>
                {notionActive ? "✓" : "○"} Notion
              </span>
              <span className={githubActive ? "text-[#00FF88]" : "text-(--qs-text-3)"}>
                {githubActive ? "✓" : "○"} GitHub
              </span>
              <span className={gmailActive ? "text-[#00FF88]" : "text-(--qs-text-3)"}>
                {gmailActive ? "✓" : "○"} Gmail {gmailOnlyPending ? "(optional)" : ""}
              </span>
            </div>
          ) : null}
          {oauthConnectRows.length > 0 ? (
            <>
              {gmailOnlyPending ? (
                <p className="mb-2 text-xs text-(--qs-text-3)">
                  Notion + GitHub connected via server tokens. Authorize Gmail below to finish Marketing/Sales email.
                </p>
              ) : null}
              <div
                className={
                  oauthConnectRows.length === 1
                    ? "grid w-full max-w-sm gap-2"
                    : "grid w-full gap-2 sm:grid-cols-3"
                }
              >
                {oauthConnectRows.map((row) => (
                  <OAuthConnectButton
                    key={row.provider_key}
                    providerKey={row.provider_key}
                    label={row.label}
                    configured={row.configured}
                    logo={<VendorGlyph providerKey={row.provider_key} />}
                  />
                ))}
              </div>
            </>
          ) : null}
        </SetupStep>

        <SetupStep
          done={marketingSwarmBuilt}
          title="Build Marketing Ops swarm"
          detail="First department colony — 4 bees wired to Execution Studio simulate mode."
        >
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busyKey !== null}
            onClick={() =>
              void runAction("build-marketing", () => buildDepartmentSwarm("marketing-ops"), "Marketing Ops swarm ready")
            }
          >
            {busyKey === "build-marketing" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
            Build Marketing Ops
          </button>
          {!allDeptsBuilt ? (
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={busyKey !== null}
              onClick={() =>
                void runAction(
                  "build-all",
                  () => buildAllDepartmentSwarms(true),
                  "All department swarms provisioned",
                )
              }
            >
              Build all 6 + Sentinel
            </button>
          ) : null}
        </SetupStep>

        <SetupStep
          done={allFirstRunsDone}
          title="Run first simulate sessions"
          detail={
            allFirstRunsDone
              ? "6/6 department playbooks verified — review outputs in Agents → Sessions."
              : `${firstRunCount}/${firstRunTotal} playbooks — start department simulate runs before any live write.`
          }
        >
          {!allFirstRunsDone
            ? (
                [
                  ["marketing-ops", "Marketing", "first-run-marketing", !marketingSwarmBuilt],
                  ["lead-waterfall", "Sales", "first-run-sales", !allDeptsBuilt],
                  ["rnd-dev", "R&D", "first-run-rnd", !allDeptsBuilt],
                  ["finance-ops", "Finance", "first-run-finance", !allDeptsBuilt],
                  ["digital-ops", "Digital", "first-run-digital", !allDeptsBuilt],
                  ["product-ship", "Product", "first-run-product", !allDeptsBuilt],
                ] as const
              ).map(([templateId, label, busy, disabledExtra]) =>
                isFirstRunCompleted(templateId) ? null : (
                  <button
                    key={templateId}
                    type="button"
                    className={`qs-btn qs-btn--sm ${templateId === "marketing-ops" ? "qs-btn--primary" : "qs-btn--ghost"}`}
                    disabled={busyKey !== null || disabledExtra}
                    onClick={() =>
                      void runAction(
                        busy,
                        async () => {
                          await startFirstRunSession(templateId);
                          window.location.href = "/agents#sessions";
                        },
                        `${label} simulate started`,
                      )
                    }
                  >
                    {busyKey === busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
                    {label}
                  </button>
                ),
              )
            : null}
          <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
            Open sessions
          </Link>
        </SetupStep>
      </ol>
    </V4Card>
  );
}
