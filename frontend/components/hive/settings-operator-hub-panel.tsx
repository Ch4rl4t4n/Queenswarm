"use client";

import { Loader2, Settings2 } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useState } from "react";

import { SettingsOperatorTrustedAutoPanel } from "@/components/hive/settings-operator-trusted-auto-panel";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4AdvancedPanel } from "@/components/ui/v4/v4-advanced-panel";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface OperatorModule {
  id: string;
  label: string;
  enabled: boolean;
  env_hint: string | null;
}

interface OperatorEnvFlag {
  key: string;
  active: boolean;
  description: string;
}

interface LiveLaneStep {
  id: string;
  lane: string;
  label: string;
  status: string;
}

interface OperatorHubSnapshot {
  enabled: boolean;
  modules: OperatorModule[];
  env_flags: OperatorEnvFlag[];
  live_lane: {
    progress_pct: number;
    trading_live_flag: boolean;
    publish_live_flag: boolean;
    steps: LiveLaneStep[];
    actions: Array<{ id: string; label: string; href?: string | null }>;
  } | null;
  publish_onboarding: {
    progress_pct: number;
    steps: Array<{
      id: string;
      label: string;
      status: string;
      detail: string;
      link: string | null;
    }>;
    flags: Record<string, boolean>;
  } | null;
  social_oauth: {
    live_publish_enabled: boolean;
    env_configured_count: number;
    active_channel_count: number;
    ready_items_count: number;
    simulate_count: number;
    channels: Array<{
      channel: string;
      label: string;
      env_configured: boolean;
      installed: boolean;
      active: boolean;
      credentials_ok: boolean;
      env_id_key: string | null;
      env_secret_key: string | null;
      console_url: string | null;
    }>;
    blockers: string[];
    prep_scripts: Record<string, string>;
  } | null;
  docs: Record<string, string>;
  next_action: {
    priority: number;
    title: string;
    why: string;
    doc: string;
    commands: string[];
    ui_link: string | null;
    step_id: string | null;
  } | null;
  daily_plan: {
    enabled: boolean;
    items: Array<{
      id: string;
      lane: string;
      title: string;
      detail: string;
      href: string | null;
      priority: number;
    }>;
  } | null;
}

interface LiveLanePreflight {
  trading: { allowed: boolean; blockers: string[] };
  publish: { allowed: boolean; blockers: string[] };
}

function SettingsOperatorHubPanelInner(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<OperatorHubSnapshot | null>(null);
  const [preflight, setPreflight] = useState<LiveLanePreflight | null>(null);
  const [loading, setLoading] = useState(true);
  const [preflightBusy, setPreflightBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await hiveGet<OperatorHubSnapshot>("settings/operator-hub");
      setSnapshot(data);
    } catch (err) {
      if (err instanceof HiveApiError && err.status === 404) {
        setSnapshot(null);
        return;
      }
      setError(err instanceof Error ? err.message : "Operator hub unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  const runPreflight = useCallback(async () => {
    setPreflightBusy(true);
    try {
      const data = await hivePostJson<LiveLanePreflight>("settings/operator-hub/preflight", {});
      setPreflight(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preflight failed.");
    } finally {
      setPreflightBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading operator hub…
      </div>
    );
  }

  if (error) {
    return (
      <V4Card>
        <p className="text-sm text-[#FF3366]">{error}</p>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <V4Card id="operator-hub">
      <V4CardHeader
        kicker="Operator"
        title="Autonomy & live lane hub"
        description="Shipped modules, env kill switches, and live prep — configure via env + Connector Vault (no secrets here)."
        actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
      />

      {snapshot.next_action ? (
        <section className="mt-4 rounded-lg border border-pollen/40 bg-pollen/5 p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-pollen">Next action</p>
          <h3 className="mt-1 text-base font-semibold text-(--qs-text)">{snapshot.next_action.title}</h3>
          <p className="mt-2 text-sm text-(--qs-muted)">{snapshot.next_action.why}</p>
          {snapshot.next_action.commands.length > 0 ? (
            <ul className="mt-3 space-y-1 font-mono text-[11px] text-cyan">
              {snapshot.next_action.commands.slice(0, 4).map((cmd) => (
                <li key={cmd}>{cmd}</li>
              ))}
            </ul>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-2">
            {snapshot.next_action.ui_link ? (
              <Link href={snapshot.next_action.ui_link} className="qs-btn qs-btn--primary qs-btn--sm">
                Open in app
              </Link>
            ) : null}
            <span className="self-center text-xs text-(--qs-text-3)">{snapshot.next_action.doc}</span>
          </div>
        </section>
      ) : null}

      {snapshot.daily_plan?.enabled && snapshot.daily_plan.items.length > 0 ? (
        <section className="mt-4 space-y-2">
          <h3 className="text-sm font-semibold text-(--qs-text)">Dnešný plán (solo)</h3>
          <ol className="space-y-1 text-xs">
            {snapshot.daily_plan.items.slice(0, 5).map((item, idx) => (
              <li key={item.id} className="flex flex-wrap items-center gap-2 rounded bg-black/20 px-2 py-1">
                <span className="font-mono text-[10px] text-(--qs-text-3)">{idx + 1}.</span>
                <V4Badge tone="info">{item.lane}</V4Badge>
                {item.href ? (
                  <Link href={item.href} className="text-cyan hover:underline">
                    {item.title}
                  </Link>
                ) : (
                  <span>{item.title}</span>
                )}
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <section className="operator-hub-modules mt-4">
        <div className="operator-hub-module-bubbles flex flex-wrap gap-2">
          {snapshot.modules.map((mod) => (
            <V4Badge key={mod.id} tone={mod.enabled ? "ok" : "info"}>
              {mod.label}
            </V4Badge>
          ))}
        </div>

        <V4AdvancedPanel
          className="operator-hub-advanced-panel"
          title="Advanced lane & OAuth"
          description="Env kill switches, live lane prep, publish onboarding, social OAuth, and trusted autopilot."
        >
      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-(--qs-text-3)">Env kill switches</h3>
        <ul className="space-y-2">
          {snapshot.env_flags.map((flag) => (
            <li
              key={flag.key}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm"
            >
              <div>
                <p className="font-mono text-xs text-cyan">{flag.key}</p>
                <p className="text-xs text-(--qs-muted)">{flag.description}</p>
              </div>
              <V4Badge tone={flag.active ? "err" : "ok"}>{flag.active ? "ON" : "OFF"}</V4Badge>
            </li>
          ))}
        </ul>
        <p className="text-xs text-(--qs-text-3)">
          Enable live flags via <span className="font-mono">scripts/operator-live-trading-prep.sh</span> after vault + simulate review.
        </p>
      </section>

      {snapshot.live_lane ? (
        <section className="mt-6 space-y-3">
          <div className="flex items-center gap-2">
            <Settings2 className="size-4 text-[#FF00AA]" aria-hidden />
            <h3 className="text-sm font-semibold text-(--qs-text)">Live lane prep {snapshot.live_lane.progress_pct}%</h3>
          </div>
          <ul className="max-h-36 space-y-1 overflow-y-auto text-xs">
            {snapshot.live_lane.steps.slice(0, 10).map((step) => (
              <li key={step.id} className="rounded bg-black/20 px-2 py-1">
                <span className="uppercase text-[10px] text-cyan">{step.lane}</span> {step.label}{" "}
                <V4Badge tone={step.status === "done" ? "ok" : "warn"}>{step.status}</V4Badge>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" disabled={preflightBusy} onClick={() => void runPreflight()}>
              {preflightBusy ? <Loader2 className="size-3 animate-spin" /> : null}
              Preflight dry-run
            </button>
            <Link href="/integrations?tab=studio#live-lane" className="qs-btn qs-btn--ghost qs-btn--sm">
              Execution Studio lane
            </Link>
          </div>
          {preflight ? (
            <div className="rounded border border-(--qs-border) bg-black/20 p-3 text-xs">
              <p>
                Trading: <V4Badge tone={preflight.trading.allowed ? "ok" : "err"}>{preflight.trading.allowed ? "ready" : "blocked"}</V4Badge>
              </p>
              {!preflight.trading.allowed ? (
                <ul className="mt-1 list-disc pl-4 text-(--qs-muted)">
                  {preflight.trading.blockers.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              ) : null}
              <p className="mt-2">
                Publish: <V4Badge tone={preflight.publish.allowed ? "ok" : "err"}>{preflight.publish.allowed ? "ready" : "blocked"}</V4Badge>
              </p>
              {!preflight.publish.allowed ? (
                <ul className="mt-1 list-disc pl-4 text-(--qs-muted)">
                  {preflight.publish.blockers.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}

      {snapshot.publish_onboarding ? (
        <section className="mt-6 space-y-3">
          <h3 className="text-sm font-semibold text-(--qs-text)">
            Publish lane onboarding {snapshot.publish_onboarding.progress_pct}%
          </h3>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-pollen"
              style={{ width: `${snapshot.publish_onboarding.progress_pct}%` }}
              role="progressbar"
              aria-valuenow={snapshot.publish_onboarding.progress_pct}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          <ul className="max-h-40 space-y-1 overflow-y-auto text-xs">
            {snapshot.publish_onboarding.steps
              .filter((step) => step.status !== "done")
              .slice(0, 5)
              .map((step) => (
                <li key={step.id} className="flex flex-wrap items-center gap-2 rounded bg-black/20 px-2 py-1">
                  <V4Badge tone={step.status === "ready" ? "gold" : step.status === "blocked" ? "err" : "info"}>
                    {step.status}
                  </V4Badge>
                  {step.link ? (
                    <Link href={step.link} className="text-cyan hover:underline">
                      {step.label}
                    </Link>
                  ) : (
                    <span>{step.label}</span>
                  )}
                </li>
              ))}
          </ul>
          <div className="flex flex-wrap gap-2">
            <Link href="/integrations?tab=studio#publish-queue" className="qs-btn qs-btn--ghost qs-btn--sm">
              Publish Queue
            </Link>
            <Link href="/integrations?tab=studio#social-publish" className="qs-btn qs-btn--ghost qs-btn--sm">
              Social publish
            </Link>
          </div>
          <p className="text-xs text-(--qs-text-3)">
            Bootstrap: <span className="font-mono">./scripts/operator-publish-lane-prep.sh</span>
          </p>
        </section>
      ) : null}

      {snapshot.social_oauth ? (
        <section className="mt-6 space-y-3">
          <h3 className="text-sm font-semibold text-(--qs-text)">Social OAuth readiness</h3>
          <p className="text-xs text-(--qs-muted)">
            Env keys: {snapshot.social_oauth.env_configured_count}/4 · Connected:{" "}
            {snapshot.social_oauth.active_channel_count} · Ready packs: {snapshot.social_oauth.ready_items_count} ·
            Simulates logged: {snapshot.social_oauth.simulate_count}
          </p>
          <ul className="space-y-1 text-xs">
            {snapshot.social_oauth.channels.map((ch) => (
              <li
                key={ch.channel}
                className="flex flex-wrap items-center justify-between gap-2 rounded bg-black/20 px-2 py-1"
              >
                <div>
                  <span>{ch.label}</span>
                  {!ch.env_configured && ch.env_id_key ? (
                    <p className="font-mono text-[10px] text-(--qs-muted)">
                      {ch.env_id_key} + {ch.env_secret_key}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  <V4Badge tone={ch.env_configured ? "ok" : "info"}>env</V4Badge>
                  <V4Badge tone={ch.installed ? "ok" : "info"}>installed</V4Badge>
                  <V4Badge tone={ch.active ? "ok" : ch.credentials_ok ? "gold" : "warn"}>
                    {ch.active ? "connected" : "connect"}
                  </V4Badge>
                  {ch.console_url && !ch.env_configured ? (
                    <a
                      href={ch.console_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-cyan hover:underline"
                    >
                      Console
                    </a>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
          {snapshot.social_oauth.blockers.length > 0 ? (
            <ul className="list-disc space-y-1 pl-4 text-xs text-(--qs-muted)">
              {snapshot.social_oauth.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-(--qs-green)">OAuth path clear — simulate or enable live when ready.</p>
          )}
          <p className="text-xs text-(--qs-text-3)">
            Probe: <span className="font-mono">./scripts/operator-social-oauth-status.sh</span>
          </p>
        </section>
      ) : null}

      <section className="rounded-lg border border-(--qs-border) bg-black/10 p-4">
        <SettingsOperatorTrustedAutoPanel />
      </section>
      </V4AdvancedPanel>
      </section>

    </V4Card>
  );
}

export const SettingsOperatorHubPanel = memo(SettingsOperatorHubPanelInner);
