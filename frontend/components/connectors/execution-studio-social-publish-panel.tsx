"use client";

import Link from "next/link";
import { ExternalLink, Loader2, Send, Sparkles } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { PublishMediaMissingBadge, PublishMediaPreview } from "@/components/connectors/publish-media-preview";
import { InfoHint } from "@/components/hive/info-hint";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { SOCIAL_PUBLISH_PANEL_HINT } from "@/lib/social-connector-operator-hints";
import { cn } from "@/lib/utils";

interface SocialChannelRow {
  channel: string;
  label: string;
  connector_slug: string;
  template_id: string;
  installed: boolean;
  active: boolean;
  credentials_ok: boolean;
  publish_tool: string;
  live_allowed: boolean;
}

interface SocialReadyItem {
  deliverable_id: string;
  title: string;
  channel: string;
  body_preview: string;
  media_url: string | null;
  media_kind: string | null;
  social_account_id: string | null;
  tags: string[];
}

interface ConnectedSocialAccount {
  id: string;
  channel: string;
  label: string;
  oauth_provider_key: string;
  connector_slug: string;
  external_user_id: string | null;
  external_username: string | null;
  profile_meta: Record<string, unknown>;
  is_default: boolean;
  status: string;
  created_at: string;
}

interface SocialPublishSnapshot {
  enabled: boolean;
  live_enabled: boolean;
  generated_at: string;
  channels: SocialChannelRow[];
  ready_items: SocialReadyItem[];
  audit?: {
    enabled: boolean;
    count: number;
    entries: {
      at: string;
      kind: string;
      message: string;
      title: string | null;
      channel: string | null;
      mode: string | null;
      ok: boolean | null;
    }[];
  } | null;
  meta_accounts?: {
    oauth_configured: boolean;
    connector_ready: boolean;
    default_ig_user_id: string | null;
    default_page_id: string | null;
    message: string;
    pages: {
      page_id: string;
      page_name: string;
      ig_user_id: string | null;
      ig_username: string | null;
    }[];
  } | null;
  x_account?: {
    oauth_configured: boolean;
    connector_ready: boolean;
    user_id: string | null;
    username: string | null;
    message: string;
  } | null;
  tiktok_account?: {
    oauth_configured: boolean;
    connector_ready: boolean;
    creator_nickname: string | null;
    max_video_post_duration_sec: number | null;
    message: string;
    review_required: boolean;
    review_note: string;
  } | null;
  connected_accounts?: {
    accounts: ConnectedSocialAccount[];
    defaults: Record<string, string>;
  } | null;
  trusted_auto?: {
    global_enabled: boolean;
    tenant_enabled: boolean;
    min_simulates_required: number;
    live_enabled: boolean;
    channels: {
      channel: string;
      mode: "manual" | "auto";
      successful_simulates: number;
      min_simulates_required: number;
      auto_eligible: boolean;
    }[];
  } | null;
  rate_limit?: {
    enabled: boolean;
    fail_closed: boolean;
    window_hours: number;
    global_used: number;
    global_max: number;
    global_remaining: number;
    redis_ok: boolean;
    channels: {
      channel: string;
      used: number;
      max_per_channel: number;
      remaining: number;
    }[];
  } | null;
  links: Record<string, string>;
}

export interface ExecutionStudioSocialPublishPanelProps {
  onError: (message: string | null) => void;
  onOpenHub?: () => void;
}

function normalizeChannelKey(raw: string): string {
  const lowered = raw.trim().toLowerCase();
  if (lowered === "x" || lowered === "x-twitter") return "twitter";
  if (lowered === "ig") return "instagram";
  if (lowered === "fb") return "facebook";
  return lowered;
}

function accountsForChannel(
  accounts: ConnectedSocialAccount[],
  channelRaw: string,
): ConnectedSocialAccount[] {
  const channel = normalizeChannelKey(channelRaw);
  return accounts.filter((row) => row.channel === channel && row.status === "active");
}

function resolveDefaultAccountId(
  item: SocialReadyItem,
  accounts: ConnectedSocialAccount[],
  defaults: Record<string, string>,
): string {
  if (item.social_account_id) return item.social_account_id;
  const channel = normalizeChannelKey(item.channel);
  const channelAccounts = accountsForChannel(accounts, channel);
  if (defaults[channel]) return defaults[channel];
  const flagged = channelAccounts.find((row) => row.is_default);
  if (flagged) return flagged.id;
  return channelAccounts[0]?.id ?? "";
}

function channelTone(row: SocialChannelRow): "ok" | "warn" | "err" | "info" {
  if (row.active) return "ok";
  if (row.installed) return "warn";
  return "err";
}

function ExecutionStudioSocialPublishPanelInner({
  onError,
  onOpenHub,
}: ExecutionStudioSocialPublishPanelProps) {
  const [snapshot, setSnapshot] = useState<SocialPublishSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [policyBusy, setPolicyBusy] = useState(false);
  const [selectedAccounts, setSelectedAccounts] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<SocialPublishSnapshot>("social-publish");
      setSnapshot(data);
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Failed to load social publish.");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  const runPublish = useCallback(
    async (item: SocialReadyItem, mode: "simulate" | "live", socialAccountId?: string) => {
      setBusyId(item.deliverable_id);
      try {
        const path =
          mode === "simulate"
            ? `social-publish/${item.deliverable_id}/simulate`
            : `social-publish/${item.deliverable_id}/publish`;
        const body: Record<string, unknown> =
          mode === "live" ? { operator_confirmed: true } : {};
        if (socialAccountId) {
          body.social_account_id = socialAccountId;
        }
        const result = await hivePostJson<{
          ok: boolean;
          message?: string;
          tiktok_status?: { status?: string; message?: string };
        }>(path, body);
        if (result.ok) {
          const tiktokNote =
            result.tiktok_status?.status && result.tiktok_status.status !== "skipped"
              ? ` · TikTok: ${result.tiktok_status.status}`
              : "";
          toast.success(
            (mode === "simulate" ? "Simulated publish OK" : "Live publish submitted") + tiktokNote,
          );
        } else {
          toast.error(result.message ?? "Publish blocked");
        }
        await load();
      } catch (exc) {
        toast.error(exc instanceof HiveApiError ? exc.message : "Publish failed");
      } finally {
        setBusyId(null);
      }
    },
    [load],
  );

  const patchTrustedAuto = useCallback(
    async (patch: { enabled?: boolean; channels?: Record<string, "manual" | "auto"> }) => {
      setPolicyBusy(true);
      try {
        const updated = await hivePatchJson<NonNullable<SocialPublishSnapshot["trusted_auto"]>>(
          "social-publish/trusted-auto",
          patch,
        );
        setSnapshot((prev) => (prev ? { ...prev, trusted_auto: updated } : prev));
        toast.success("Trusted auto-publish policy saved");
      } catch (exc) {
        toast.error(exc instanceof HiveApiError ? exc.message : "Failed to save trusted auto policy");
      } finally {
        setPolicyBusy(false);
      }
    },
    [],
  );

  const toggleTenantTrustedAuto = useCallback(() => {
    const current = snapshot?.trusted_auto?.tenant_enabled ?? false;
    void patchTrustedAuto({ enabled: !current });
  }, [patchTrustedAuto, snapshot?.trusted_auto?.tenant_enabled]);

  const setChannelMode = useCallback(
    (channel: string, mode: "manual" | "auto") => {
      void patchTrustedAuto({ channels: { [channel]: mode } });
    },
    [patchTrustedAuto],
  );

  const setDefaultAccount = useCallback(
    async (accountId: string) => {
      try {
        await hivePostJson(`social-publish/accounts/${accountId}/default`, {});
        toast.success("Default account saved");
        await load();
      } catch (exc) {
        toast.error(exc instanceof HiveApiError ? exc.message : "Failed to set default account");
      }
    },
    [load],
  );

  const connectedAccounts = snapshot?.connected_accounts?.accounts ?? [];
  const accountDefaults = snapshot?.connected_accounts?.defaults ?? {};

  function accountDetailLine(account: ConnectedSocialAccount): string | null {
    const meta = account.profile_meta ?? {};
    const ig = typeof meta.ig_user_id === "string" ? meta.ig_user_id : "";
    const page = typeof meta.page_id === "string" ? meta.page_id : "";
    if (ig) return `IG ${ig}${page ? ` · Page ${page}` : ""}`;
    if (page) return `Page ${page}`;
    if (account.external_username) return account.external_username;
    return null;
  }

  function isIncompleteMetaAccount(account: ConnectedSocialAccount): boolean {
    return (
      account.channel === "instagram" &&
      (account.label === "Meta account" || !accountDetailLine(account))
    );
  }

  if (loading) {
    return (
      <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden>
        <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin" /> Loading social channels…
        </p>
      </div>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <V4Card id="social-publish" className="shrink-0 ring-1 ring-pollen/25">
      <V4CardHeader
        kicker="Multi-account · Phase C"
        title="Social publish — IG · FB · X · TikTok · Newsletter"
        description="Neobmedzené účty na platformu. Pripoj + Instagram / + X / + TikTok — každé OAuth pridá nový účet. Pri packu vyber „Publikuješ ako“."
        hint={
          <InfoHint
            title={SOCIAL_PUBLISH_PANEL_HINT.title}
            description={SOCIAL_PUBLISH_PANEL_HINT.description}
            options={SOCIAL_PUBLISH_PANEL_HINT.options}
            className="hive-inline-hint"
          />
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <V4Badge tone={snapshot.live_enabled ? "warn" : "ok"}>
          Live API {snapshot.live_enabled ? "enabled" : "simulate-only"}
        </V4Badge>
        <Link href={snapshot.links.marketplace ?? "/integrations?tab=marketplace"} className="qs-btn qs-btn--ghost qs-btn--sm">
          <ExternalLink className="size-4" aria-hidden />
          Install connectors
        </Link>
        <form method="POST" action="/api/auth/connect/instagram_graph" className="inline">
          <button
            type="submit"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={snapshot.meta_accounts?.oauth_configured === false}
            title={
              snapshot.meta_accounts?.oauth_configured === false
                ? "Set OAUTH_META_* in hive env first"
                : "Launch Meta hosted OAuth for Instagram Graph"
            }
          >
            Connect Instagram (Meta)
          </button>
        </form>
        <form method="POST" action="/api/auth/connect/twitter_api_v2" className="inline">
          <button
            type="submit"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={snapshot.x_account?.oauth_configured === false}
            title={
              snapshot.x_account?.oauth_configured === false
                ? "Set OAUTH_X_* in hive env first"
                : "Launch X hosted OAuth for tweet publish"
            }
          >
            Connect X (Twitter)
          </button>
        </form>
        <form method="POST" action="/api/auth/connect/tiktok_content" className="inline">
          <button
            type="submit"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={snapshot.tiktok_account?.oauth_configured === false}
            title={
              snapshot.tiktok_account?.oauth_configured === false
                ? "Set OAUTH_TIKTOK_* in hive env first"
                : "Launch TikTok OAuth for video publish"
            }
          >
            Connect TikTok
          </button>
        </form>
        {onOpenHub ? (
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={onOpenHub}>
            Hub setup
          </button>
        ) : (
          <Link
            href={snapshot.links.connector_hub ?? "/integrations?tab=hub#oauth-consent"}
            className="qs-btn qs-btn--ghost qs-btn--sm"
          >
            Hub setup
          </Link>
        )}
      </div>

      <div
        id="connected-social-accounts"
        className="mb-4 rounded-lg border border-pollen/40 bg-pollen/5 px-3 py-4 text-sm shadow-[0_0_24px_rgba(255,184,0,0.08)]"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-semibold text-pollen">
              Pripojené účty · Connected accounts ({connectedAccounts.length})
            </p>
            <p className="mt-1 text-xs text-(--qs-muted)">
              Každé OAuth Connect <strong className="text-(--qs-text)">pridá nový účet</strong> (neprepisuje
              starý). Pri publikovaní vyber „Publikuješ ako“ na packu.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <form method="POST" action="/api/auth/connect/instagram_graph" className="inline">
              <button
                type="submit"
                className="qs-btn qs-btn--primary qs-btn--sm"
                disabled={snapshot.meta_accounts?.oauth_configured === false}
              >
                + Instagram
              </button>
            </form>
            <form method="POST" action="/api/auth/connect/facebook_graph" className="inline">
              <button type="submit" className="qs-btn qs-btn--ghost qs-btn--sm">
                + Facebook
              </button>
            </form>
            <form method="POST" action="/api/auth/connect/twitter_api_v2" className="inline">
              <button
                type="submit"
                className="qs-btn qs-btn--primary qs-btn--sm"
                disabled={snapshot.x_account?.oauth_configured === false}
              >
                + X
              </button>
            </form>
            <form method="POST" action="/api/auth/connect/tiktok_content" className="inline">
              <button
                type="submit"
                className="qs-btn qs-btn--primary qs-btn--sm"
                disabled={snapshot.tiktok_account?.oauth_configured === false}
              >
                + TikTok
              </button>
            </form>
          </div>
        </div>

        {connectedAccounts.length === 0 ? (
          <p className="mt-3 text-xs text-pollen">
            Zatiaľ žiadny účet — klikni + Instagram, + X alebo + TikTok vyššie.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {connectedAccounts.map((account) => {
              const detail = accountDetailLine(account);
              const incomplete = isIncompleteMetaAccount(account);
              return (
                <li
                  key={account.id}
                  className={cn(
                    "flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2 text-xs",
                    incomplete ? "border-pollen/60 bg-pollen/10" : "border-(--qs-border)/60 bg-black/20",
                  )}
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold capitalize text-(--qs-text)">{account.channel}</span>
                      {account.is_default ? <V4Badge tone="ok">default</V4Badge> : null}
                      {incomplete ? <V4Badge tone="warn">needs reconnect</V4Badge> : null}
                    </div>
                    <p className="mt-0.5 font-mono text-cyan">{account.label}</p>
                    {detail ? (
                      <p className="mt-0.5 font-mono text-(--qs-text-3)">{detail}</p>
                    ) : incomplete ? (
                      <p className="mt-0.5 text-pollen">
                        Chýba IG/Page ID — znova Connect Instagram (Meta) s Page + IG business účtom.
                      </p>
                    ) : null}
                    <p className="mt-1 font-mono text-[10px] text-(--qs-muted)">id: {account.id.slice(0, 8)}…</p>
                  </div>
                  <div className="flex flex-col gap-1">
                    {!account.is_default ? (
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--xs"
                        onClick={() => void setDefaultAccount(account.id)}
                      >
                        Set default
                      </button>
                    ) : null}
                    <form method="POST" action={`/api/auth/connect/${account.oauth_provider_key}`} className="inline">
                      <button type="submit" className="qs-btn qs-btn--ghost qs-btn--xs">
                        Reconnect
                      </button>
                    </form>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {snapshot.trusted_auto ? (
        <div className="mb-4 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-semibold text-(--qs-text)">Trusted auto-publish (Phase G)</p>
              <p className="mt-1 text-xs text-(--qs-muted)">
                Auto-live after {snapshot.trusted_auto.min_simulates_required}+ successful simulates per channel.
                Scheduled tick can publish live when eligible.
              </p>
            </div>
            <button
              type="button"
              className={cn(
                "qs-btn qs-btn--sm",
                snapshot.trusted_auto.tenant_enabled ? "qs-btn--primary" : "qs-btn--ghost",
              )}
              disabled={
                policyBusy ||
                !snapshot.trusted_auto.global_enabled ||
                !snapshot.trusted_auto.live_enabled
              }
              onClick={() => toggleTenantTrustedAuto()}
            >
              {policyBusy ? <Loader2 className="size-4 animate-spin" /> : null}
              {snapshot.trusted_auto.tenant_enabled ? "Auto enabled" : "Enable auto"}
            </button>
          </div>
          {!snapshot.trusted_auto.global_enabled ? (
            <p className="mt-2 text-xs text-pollen">
              Set SOCIAL_PUBLISH_TRUSTED_AUTO_ENABLED=true in prod env after OAuth + manual simulates.
            </p>
          ) : !snapshot.trusted_auto.live_enabled ? (
            <p className="mt-2 text-xs text-pollen">Requires SOCIAL_PUBLISH_LIVE_ENABLED=true.</p>
          ) : null}
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {snapshot.trusted_auto.channels.map((row) => (
              <li
                key={row.channel}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-(--qs-border)/60 px-2 py-2 text-xs"
              >
                <div>
                  <span className="font-semibold capitalize text-(--qs-text)">{row.channel}</span>
                  <p className="font-mono text-(--qs-muted)">
                    {row.successful_simulates}/{row.min_simulates_required} simulates
                    {row.auto_eligible ? (
                      <span className="ml-1 text-(--qs-green)">· auto-ready</span>
                    ) : null}
                  </p>
                </div>
                <div className="flex gap-1">
                  <button
                    type="button"
                    className={cn(
                      "qs-btn qs-btn--xs",
                      row.mode === "manual" ? "qs-btn--primary" : "qs-btn--ghost",
                    )}
                    disabled={policyBusy || !snapshot.trusted_auto?.tenant_enabled}
                    onClick={() => setChannelMode(row.channel, "manual")}
                  >
                    Manual
                  </button>
                  <button
                    type="button"
                    className={cn(
                      "qs-btn qs-btn--xs",
                      row.mode === "auto" ? "qs-btn--primary" : "qs-btn--ghost",
                    )}
                    disabled={
                      policyBusy ||
                      !snapshot.trusted_auto?.tenant_enabled ||
                      row.successful_simulates < row.min_simulates_required
                    }
                    onClick={() => setChannelMode(row.channel, "auto")}
                  >
                    Auto
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {snapshot.rate_limit?.enabled ? (
        <div className="mb-4 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-3 text-xs">
          <p className="font-semibold text-(--qs-text)">
            Live rate limits ({snapshot.rate_limit.window_hours}h window)
          </p>
          {!snapshot.rate_limit.redis_ok ? (
            <p className="mt-1 text-pollen">Rate limiter unavailable — live may be blocked (fail-closed).</p>
          ) : (
            <p className="mt-1 font-mono text-(--qs-muted)">
              Global {snapshot.rate_limit.global_used}/{snapshot.rate_limit.global_max} · remaining{" "}
              {snapshot.rate_limit.global_remaining}
            </p>
          )}
          <ul className="mt-2 grid gap-1 sm:grid-cols-2">
            {snapshot.rate_limit.channels.map((row) => (
              <li key={row.channel} className="flex justify-between gap-2 font-mono text-[10px] text-(--qs-text-3)">
                <span className="capitalize">{row.channel}</span>
                <span className={row.remaining === 0 ? "text-(--qs-red)" : "text-cyan"}>
                  {row.used}/{row.max_per_channel}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {snapshot.meta_accounts?.connector_ready && snapshot.meta_accounts.pages.length > 0 ? (
        <div className="mb-4 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-3 text-xs">
          <p className="font-semibold text-(--qs-text)">Meta accounts (auto-resolve ig_user_id / page_id)</p>
          <ul className="mt-2 space-y-1 font-mono text-(--qs-text-3)">
            {snapshot.meta_accounts.pages.map((page) => (
              <li key={page.page_id}>
                Page {page.page_name} · {page.page_id}
                {page.ig_user_id ? (
                  <span className="text-cyan">
                    {" "}
                    · IG {page.ig_username ? `@${page.ig_username}` : page.ig_user_id}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : snapshot.meta_accounts && !snapshot.meta_accounts.oauth_configured ? (
        <p className="mb-4 text-xs text-pollen">
          Set OAUTH_META_CLIENT_ID + OAUTH_META_CLIENT_SECRET in .env.prod.oauth → redeploy → Connect Instagram in Connector Hub.
        </p>
      ) : null}
      {snapshot.x_account?.connector_ready && snapshot.x_account.username ? (
        <div className="mb-4 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-3 text-xs">
          <p className="font-semibold text-(--qs-text)">X account connected</p>
          <p className="mt-1 font-mono text-cyan">@{snapshot.x_account.username}</p>
        </div>
      ) : snapshot.x_account && !snapshot.x_account.oauth_configured ? (
        <p className="mb-4 text-xs text-(--qs-muted)">
          X OAuth: set OAUTH_X_CLIENT_ID + OAUTH_X_CLIENT_SECRET in .env.prod.oauth → Connect in Hub.
        </p>
      ) : null}
      {snapshot.tiktok_account?.connector_ready && snapshot.tiktok_account.creator_nickname ? (
        <div className="mb-4 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-3 text-xs">
          <p className="font-semibold text-(--qs-text)">TikTok creator</p>
          <p className="mt-1 font-mono text-cyan">@{snapshot.tiktok_account.creator_nickname}</p>
          {snapshot.tiktok_account.review_required ? (
            <p className="mt-1 text-pollen">{snapshot.tiktok_account.review_note}</p>
          ) : null}
        </div>
      ) : snapshot.tiktok_account && !snapshot.tiktok_account.oauth_configured ? (
        <p className="mb-4 text-xs text-(--qs-muted)">
          TikTok OAuth: OAUTH_TIKTOK_CLIENT_KEY + OAUTH_TIKTOK_CLIENT_SECRET → Connect in Hub (review required for live).
        </p>
      ) : null}
      <ul className="mb-4 grid gap-2 sm:grid-cols-2">
        {snapshot.channels.map((row) => (
          <li
            key={row.channel}
            className={cn(
              "rounded-lg border border-(--qs-border) bg-black/20 px-3 py-3 text-sm",
              row.active && "border-(--qs-green)/30",
            )}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-(--qs-text)">{row.label}</span>
              <V4Badge tone={channelTone(row)}>{row.active ? "ready" : row.installed ? "needs OAuth" : "not installed"}</V4Badge>
            </div>
            <p className="mt-1 font-mono text-xs text-cyan">{row.connector_slug}</p>
            <p className="mt-1 text-xs text-(--qs-muted)">Tool: {row.publish_tool}</p>
          </li>
        ))}
      </ul>
      <div className="space-y-3">
        <p className="text-sm font-semibold text-(--qs-text)">Approved packs ready to publish</p>
        {snapshot.ready_items.length === 0 ? (
          <p className="text-sm text-(--qs-muted)">
            No approved items yet — approve packs in{" "}
            <Link href={snapshot.links.publish_queue ?? "/integrations?tab=studio"} className="text-cyan underline">
              Publish Queue
            </Link>
            .
          </p>
        ) : (
          snapshot.ready_items.map((item) => {
            const channelAccounts = accountsForChannel(connectedAccounts, item.channel);
            const selectedAccountId =
              selectedAccounts[item.deliverable_id] ??
              resolveDefaultAccountId(item, connectedAccounts, accountDefaults);
            const selectedAccount =
              channelAccounts.find((row) => row.id === selectedAccountId) ?? channelAccounts[0] ?? null;
            return (
            <article
              key={item.deliverable_id}
              className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-3 text-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-(--qs-text)">{item.title}</p>
                  <p className="mt-1 text-xs text-(--qs-muted)">Channel: {item.channel}</p>
                  <div className="mt-3 rounded-md border border-cyan/30 bg-cyan/5 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-cyan">
                      Publikuješ ako · Publish as
                    </p>
                    {channelAccounts.length > 0 ? (
                      <>
                        <select
                          aria-label="Publish as social account"
                          className="mt-2 block w-full max-w-md rounded-md border border-(--qs-border) bg-black/40 px-2 py-2 font-mono text-sm text-(--qs-text)"
                          value={selectedAccountId}
                          onChange={(event) =>
                            setSelectedAccounts((prev) => ({
                              ...prev,
                              [item.deliverable_id]: event.target.value,
                            }))
                          }
                        >
                          {channelAccounts.map((account) => (
                            <option key={account.id} value={account.id}>
                              {account.label}
                              {account.is_default ? " (default)" : ""}
                            </option>
                          ))}
                        </select>
                        {selectedAccount && isIncompleteMetaAccount(selectedAccount) ? (
                          <p className="mt-2 text-xs text-pollen">
                            Účet nemá IG ID — reconnect Instagram pred live publish.
                          </p>
                        ) : null}
                        {channelAccounts.length === 1 ? (
                          <p className="mt-2 text-xs text-(--qs-muted)">
                            1 účet pre {item.channel} — + Instagram / + X / + TikTok pridá ďalší.
                          </p>
                        ) : null}
                      </>
                    ) : (
                      <p className="mt-2 text-xs text-pollen">
                        Žiadny pripojený účet pre {item.channel} — najprv + Instagram / + X / + TikTok vyššie.
                      </p>
                    )}
                  </div>
                  <p className="mt-2 line-clamp-3 text-(--qs-text-3)">{item.body_preview}</p>
                  <div className="mt-2 max-w-xs">
                    <PublishMediaPreview url={item.media_url} channel={item.channel} title={item.title} compact />
                    <PublishMediaMissingBadge channel={item.channel} mediaUrl={item.media_url} />
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm"
                    disabled={busyId === item.deliverable_id || (channelAccounts.length > 0 && !selectedAccountId)}
                    onClick={() => void runPublish(item, "simulate", selectedAccountId || undefined)}
                  >
                    {busyId === item.deliverable_id ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <Sparkles className="size-4" aria-hidden />
                    )}
                    Simulate
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={
                      !snapshot.live_enabled ||
                      busyId === item.deliverable_id ||
                      (channelAccounts.length > 0 && !selectedAccountId)
                    }
                    onClick={() => void runPublish(item, "live", selectedAccountId || undefined)}
                  >
                    <Send className="size-4" aria-hidden />
                    Live
                  </button>
                </div>
              </div>
            </article>
            );
          })
        )}
      </div>
      {snapshot.audit?.enabled && snapshot.audit.entries.length > 0 ? (
        <div className="mt-6 space-y-2 border-t border-(--qs-border) pt-4">
          <p className="text-sm font-semibold text-(--qs-text)">Publish audit (recent)</p>
          <ul className="max-h-48 space-y-2 overflow-auto">
            {snapshot.audit.entries.map((entry) => (
              <li key={`${entry.at}-${entry.kind}-${entry.message}`} className="rounded-lg border border-(--qs-border) bg-black/15 px-3 py-2 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-(--qs-text-3)">{entry.at.slice(0, 19)}</span>
                  <V4Badge tone={entry.ok === false ? "err" : entry.ok ? "ok" : "info"}>{entry.kind}</V4Badge>
                </div>
                <p className="mt-1 text-(--qs-text)">{entry.title ?? entry.message}</p>
                {entry.channel ? <p className="mt-1 text-(--qs-muted)">{entry.channel}{entry.mode ? ` · ${entry.mode}` : ""}</p> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </V4Card>
  );
}

export const ExecutionStudioSocialPublishPanel = memo(ExecutionStudioSocialPublishPanelInner);
ExecutionStudioSocialPublishPanel.displayName = "ExecutionStudioSocialPublishPanel";
