"use client";

import { CheckCircle2Icon, Loader2Icon, RadioIcon, ShieldCheckIcon } from "lucide-react";
import type { FormEvent } from "react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hivePostJson } from "@/lib/api";
import { VAULT_VENDOR_PRESETS, type VaultVendorPreset } from "@/lib/connectors-vault-presets";
import { isHttpsProbeUrl, normalizeVaultSlug } from "@/lib/connectors-vault-utils";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

type VaultKind = "oauth2" | "api_key";

interface PingResponse {
  slug: string;
  ok: boolean;
}

interface ProbeResponse {
  status_code: number;
  content_type?: string | null;
}

/** Seal MCP connector credentials, validate handshake (ping), rotate OAuth, and GET egress probes (dashboard JWT). */
export function ConnectorsVaultPanel(): JSX.Element {
  const [slug, setSlug] = useState("");
  const [label, setLabel] = useState("");
  const [kind, setKind] = useState<VaultKind>("oauth2");
  const [apiKey, setApiKey] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [refreshToken, setRefreshToken] = useState("");
  const [tokenEndpoint, setTokenEndpoint] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [refreshSlug, setRefreshSlug] = useState("");
  const [testSlug, setTestSlug] = useState("");
  const [probeSlug, setProbeSlug] = useState("");
  const [probeUrl, setProbeUrl] = useState("");
  const [ephemeralApiKey, setEphemeralApiKey] = useState("");
  const [ephemeralOAuthToken, setEphemeralOAuthToken] = useState("");
  const [useEphemeralPing, setUseEphemeralPing] = useState(false);

  const [vaultBusy, setVaultBusy] = useState(false);
  const [oauthBusy, setOauthBusy] = useState(false);
  const [pingBusy, setPingBusy] = useState(false);
  const [probeBusy, setProbeBusy] = useState(false);

  const [vaultInlineErr, setVaultInlineErr] = useState<string | null>(null);
  const [oauthInlineErr, setOauthInlineErr] = useState<string | null>(null);
  const [pingInlineErr, setPingInlineErr] = useState<string | null>(null);
  const [pingInlineOk, setPingInlineOk] = useState<string | null>(null);
  const [probeInlineErr, setProbeInlineErr] = useState<string | null>(null);
  const [probeInlineOk, setProbeInlineOk] = useState<string | null>(null);
  const [presetHint, setPresetHint] = useState<string | null>(null);
  const [presetDocsUrl, setPresetDocsUrl] = useState<string | null>(null);

  const resetSecrets = useCallback(() => {
    setApiKey("");
    setAccessToken("");
    setRefreshToken("");
    setClientSecret("");
  }, []);

  const applyVendorPreset = useCallback((p: VaultVendorPreset) => {
    setSlug(p.slug);
    setLabel(p.label);
    setKind(p.kind);
    setTokenEndpoint(p.tokenEndpoint ?? "");
    setAccessToken("");
    setRefreshToken("");
    setApiKey("");
    setClientId("");
    setClientSecret("");
    setRefreshSlug(p.slug);
    setTestSlug(p.slug);
    setProbeSlug(p.slug);
    setProbeUrl(p.probeSuggestion ?? "");
    setPresetHint(p.scopesHint);
    setPresetDocsUrl(p.docsUrl);
    setVaultInlineErr(null);
    setPingInlineErr(null);
    setPingInlineOk(null);
    setOauthInlineErr(null);
    setProbeInlineErr(null);
    setProbeInlineOk(null);
  }, []);

  async function submitVault(ev: FormEvent): Promise<void> {
    ev.preventDefault();
    const s = normalizeVaultSlug(slug);
    if (!s) {
      toast.error("Slug required.");
      setVaultInlineErr("Enter a connector slug before sealing.");
      return;
    }
    setVaultInlineErr(null);
    setVaultBusy(true);
    try {
      await hivePostJson<{ ok: string }>("connectors/vault", {
        slug: s,
        label: label.trim() || null,
        kind,
        api_key: kind === "api_key" ? apiKey.trim() || null : null,
        oauth2_access_token: kind === "oauth2" ? accessToken.trim() || null : null,
        oauth2_refresh_token: kind === "oauth2" ? refreshToken.trim() || null : null,
        oauth2_token_endpoint: kind === "oauth2" ? tokenEndpoint.trim() || null : null,
        oauth2_client_id: kind === "oauth2" ? clientId.trim() || null : null,
        oauth2_client_secret: kind === "oauth2" ? clientSecret.trim() || null : null,
      });
      toast.success(`Vault sealed · ${s}`);
      resetSecrets();
      setRefreshSlug((prev) => prev.trim() || s);
      setTestSlug((prev) => prev.trim() || s);
      setProbeSlug((prev) => prev.trim() || s);
      setPingInlineErr(null);
      setPingInlineOk(null);
      setProbeInlineErr(null);
      setProbeInlineOk(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Vault upsert failed.";
      toast.error(msg);
      setVaultInlineErr(msg);
    } finally {
      setVaultBusy(false);
    }
  }

  async function runOAuthRefresh(ev: FormEvent): Promise<void> {
    ev.preventDefault();
    const cs = normalizeVaultSlug(refreshSlug);
    if (!cs) {
      toast.error("Connector slug required.");
      setOauthInlineErr("Slug required for refresh.");
      return;
    }
    setOauthInlineErr(null);
    setOauthBusy(true);
    try {
      await hivePostJson<Record<string, unknown>>("connectors/oauth/token", {
        grant_type: "refresh_token",
        connector_slug: cs,
      });
      toast.success(`OAuth refreshed · ${cs} (tokens stored server-side)`);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Refresh failed.";
      toast.error(msg);
      setOauthInlineErr(msg);
    } finally {
      setOauthBusy(false);
    }
  }

  async function runPing(ev: FormEvent): Promise<void> {
    ev.preventDefault();
    const ps = normalizeVaultSlug(testSlug);
    if (!ps) {
      setPingInlineErr("Enter the slug to ping.");
      setPingInlineOk(null);
      return;
    }
    setPingBusy(true);
    setPingInlineErr(null);
    setPingInlineOk(null);
    try {
      let body: Record<string, string | undefined> | undefined;
      if (useEphemeralPing) {
        const ak = ephemeralApiKey.trim();
        const ot = ephemeralOAuthToken.trim();
        if (!ak && !ot) {
          throw new Error("Ephemeral ping requires an API key or OAuth access token.");
        }
        body = {};
        if (ak) {
          body.api_key = ak;
        }
        if (ot) {
          body.oauth2_access_token = ot;
        }
      }
      const payload = await hivePostJson<PingResponse>(
        `connectors/${encodeURIComponent(ps)}/ping`,
        body ?? {},
      );
      const okText = payload.ok
        ? `Handshake OK · ${payload.slug} — adapter reported healthy ping.`
        : `Handshake reported not OK · ${payload.slug} — inspect connector logs / manifest.`;
      setPingInlineOk(okText);
      toast.success(payload.ok ? `Ping OK · ${payload.slug}` : `Ping weak signal · ${payload.slug}`);
      if (useEphemeralPing) {
        setEphemeralApiKey("");
        setEphemeralOAuthToken("");
      }
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Ping failed.";
      setPingInlineErr(msg);
      toast.error(msg);
    } finally {
      setPingBusy(false);
    }
  }

  async function runProbe(ev: FormEvent): Promise<void> {
    ev.preventDefault();
    const cs = normalizeVaultSlug(probeSlug);
    const url = probeUrl.trim();
    if (!cs) {
      setProbeInlineErr("Connector slug selects which vault row supplies Authorization headers.");
      setProbeInlineOk(null);
      return;
    }
    if (!isHttpsProbeUrl(url)) {
      setProbeInlineErr("Probe URL must be a valid https:// URL.");
      setProbeInlineOk(null);
      return;
    }
    setProbeBusy(true);
    setProbeInlineErr(null);
    setProbeInlineOk(null);
    try {
      const row = await hivePostJson<ProbeResponse>("connectors/invoke-probe", {
        url,
        connector_slug: cs,
      });
      const ct = row.content_type ?? "unknown";
      setProbeInlineOk(`GET ${url.slice(0, 72)}${url.length > 72 ? "…" : ""} → HTTP ${row.status_code} · ${ct}`);
      toast.success(`Probe OK · HTTP ${row.status_code}`);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Probe failed.";
      setProbeInlineErr(msg);
      toast.error(msg);
    } finally {
      setProbeBusy(false);
    }
  }

  return (
    <V4Card>
      <V4CardHeader
        title="Connector vault · handshake wizard"
        description="AES-sealed rows scoped to your dashboard user — ciphertext never echoes back over JSON. Desktop: dense columns · Mobile: stacked with 44px tap targets."
        actions={
          <div className="flex flex-wrap gap-2">
            <V4Badge tone="gold">
              <ShieldCheckIcon className="mr-1 inline h-3.5 w-3.5" aria-hidden />
              1 Seal
            </V4Badge>
            <V4Badge tone="info">
              <RadioIcon className="mr-1 inline h-3.5 w-3.5" aria-hidden />
              2 Ping
            </V4Badge>
            <V4Badge tone="ok">
              <CheckCircle2Icon className="mr-1 inline h-3.5 w-3.5" aria-hidden />
              3 Rotate / probe
            </V4Badge>
          </div>
        }
      />

      <div className="mb-6 v4-learning-panel">
        <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#EEEEFF]">
              Phase 3 vendor presets
            </h3>
            <p className="font-[family-name:var(--font-poppins)] text-xs text-(--qs-text-3)">
              One tap fills slug, OAuth token endpoint (when applicable), and suggested HTTPS probe — you still complete consent out-of-band with the vendor,
              then <strong className="text-pollen">Seal → Ping → Refresh</strong> here.
            </p>
          </div>
        </div>
        <div className="-mx-1 flex gap-2 overflow-x-auto pb-1 md:flex-wrap">
          {VAULT_VENDOR_PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              data-qs-vault-preset={p.slug}
              className="qs-btn qs-btn--ghost qs-btn--sm shrink-0 touch-manipulation"
              onClick={() => applyVendorPreset(p)}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-(--qs-text-3)">
          <span className="font-mono text-cyan">Docs · Google / Microsoft OAuth</span>
          <a
            href="https://developers.google.com/identity/protocols/oauth2"
            target="_blank"
            rel="noreferrer"
            className="font-semibold text-pollen underline-offset-2 hover:underline"
          >
            Google OAuth2
          </a>
          <a
            href="https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow"
            target="_blank"
            rel="noreferrer"
            className="font-semibold text-pollen underline-offset-2 hover:underline"
          >
            Microsoft auth code
          </a>
        </div>
        {presetHint ? (
          <p
            className="mt-4 rounded-xl border border-pollen/25 bg-pollen/5 px-3 py-2 font-[family-name:var(--font-poppins)] text-xs leading-relaxed text-(--qs-text-2)"
            role="status"
          >
            <span className="font-semibold text-pollen">Selected preset · </span>
            {presetHint}{" "}
            {presetDocsUrl ? (
              <a href={presetDocsUrl} target="_blank" rel="noreferrer" className="text-cyan underline">
                Vendor docs ↗
              </a>
            ) : null}
          </p>
        ) : null}
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <form onSubmit={(e) => void submitVault(e)} className="v4-learning-panel space-y-4">
          <h3 className="text-sm font-semibold text-pollen">Seal credentials</h3>
          {vaultInlineErr ? (
            <p className="rounded-xl border border-danger/35 bg-black/65 px-3 py-2 text-sm text-danger" role="alert">
              {vaultInlineErr}
            </p>
          ) : null}
          <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]" htmlFor="qs-vault-connector-slug">
            Connector slug
            <input
              id="qs-vault-connector-slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              className="qs-input min-h-[44px] font-mono text-sm"
              placeholder="gmail_workspace"
              required
            />
          </label>
          <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
            Label (optional)
            <input value={label} onChange={(e) => setLabel(e.target.value)} className="qs-input min-h-[44px] text-sm" />
          </label>
          <div className="flex gap-2">
            {(["oauth2", "api_key"] as const).map((k) => (
              <button
                key={k}
                type="button"
                className={cn(
                  "flex-1 rounded-xl border px-3 py-3 font-[family-name:var(--font-poppins)] text-xs font-semibold touch-manipulation min-h-[44px]",
                  kind === k ? "border-pollen text-pollen bg-pollen/10" : "border-(--qs-border) text-(--qs-text-3)",
                )}
                onClick={() => setKind(k)}
              >
                {k === "oauth2" ? "OAuth2" : "API key"}
              </button>
            ))}
          </div>
          {kind === "api_key" ? (
            <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
              API key
              <input
                type="password"
                autoComplete="off"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="qs-input min-h-[44px] font-mono text-sm"
              />
            </label>
          ) : (
            <div className="space-y-3">
              <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
                Access token (optional if refresh present)
                <input
                  type="password"
                  autoComplete="off"
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  className="qs-input min-h-[44px] font-mono text-sm"
                />
              </label>
              <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
                Refresh token
                <input
                  type="password"
                  autoComplete="off"
                  value={refreshToken}
                  onChange={(e) => setRefreshToken(e.target.value)}
                  className="qs-input min-h-[44px] font-mono text-sm"
                />
              </label>
              <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]" htmlFor="qs-vault-token-endpoint">
                Token endpoint
                <input
                  id="qs-vault-token-endpoint"
                  value={tokenEndpoint}
                  onChange={(e) => setTokenEndpoint(e.target.value)}
                  className="qs-input min-h-[44px] font-mono text-xs"
                  placeholder="https://oauth2.googleapis.com/token"
                />
              </label>
              <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
                Client id
                <input value={clientId} onChange={(e) => setClientId(e.target.value)} className="qs-input min-h-[44px] font-mono text-sm" />
              </label>
              <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
                Client secret
                <input
                  type="password"
                  autoComplete="off"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  className="qs-input min-h-[44px] font-mono text-sm"
                />
              </label>
            </div>
          )}
          <button
            type="submit"
            disabled={vaultBusy}
            className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-2xl border border-pollen/70 bg-pollen px-4 py-3 font-[family-name:var(--font-poppins)] text-sm font-semibold text-black hover:brightness-105 disabled:opacity-40 touch-manipulation"
          >
            {vaultBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : null}
            Seal vault row
          </button>
        </form>

        <div className="flex flex-col gap-6">
          <form onSubmit={(e) => void runPing(e)} className="v4-learning-panel space-y-4">
            <h3 className="text-sm font-semibold text-pollen">Test handshake (vault ping)</h3>
            <p className="font-[family-name:var(--font-poppins)] text-xs text-(--qs-text-3)">
              Calls <span className="font-mono text-[11px] text-pollen">POST /connectors/&lt;slug&gt;/ping</span> — vault-backed unless you enable a
              one-shot ephemeral secret for staging only.
            </p>
            <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
              Slug to ping
              <input
                value={testSlug}
                onChange={(e) => setTestSlug(e.target.value)}
                className="qs-input min-h-[44px] font-mono text-sm"
                placeholder="matches sealed row"
                required
              />
            </label>
            <label className="flex min-h-[44px] cursor-pointer items-center gap-3 rounded-xl border border-(--qs-border) px-3 py-2 text-xs text-(--qs-text-2) touch-manipulation">
              <input type="checkbox" checked={useEphemeralPing} onChange={(e) => setUseEphemeralPing(e.target.checked)} className="accent-cyan" />
              Ephemeral secrets (not stored — cleared after success)
            </label>
            {useEphemeralPing ? (
              <div className="space-y-3 rounded-xl border border-magenta/25 bg-magenta/5 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-magenta">One-shot override</p>
                <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
                  API key (optional)
                  <input
                    type="password"
                    autoComplete="off"
                    value={ephemeralApiKey}
                    onChange={(e) => setEphemeralApiKey(e.target.value)}
                    className="qs-input min-h-[44px] font-mono text-sm"
                  />
                </label>
                <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
                  OAuth access token (optional)
                  <input
                    type="password"
                    autoComplete="off"
                    value={ephemeralOAuthToken}
                    onChange={(e) => setEphemeralOAuthToken(e.target.value)}
                    className="qs-input min-h-[44px] font-mono text-sm"
                  />
                </label>
              </div>
            ) : null}
            <button
              type="submit"
              disabled={pingBusy}
              className="qs-btn qs-btn--primary w-full touch-manipulation"
            >
              {pingBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : null}
              Run ping
            </button>
            {pingInlineErr ? (
              <p className="rounded-xl border border-danger/35 bg-black/65 px-3 py-2 text-sm text-danger" role="alert">
                {pingInlineErr}
              </p>
            ) : null}
            {pingInlineOk ? (
              <p className="rounded-xl border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-200" role="status">
                {pingInlineOk}
              </p>
            ) : null}
          </form>

          <form onSubmit={(e) => void runOAuthRefresh(e)} className="v4-learning-panel space-y-4">
            <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen">Rotate access token</h3>
            <p className="font-[family-name:var(--font-poppins)] text-xs text-(--qs-text-3)">
              Uses vaulted refresh token + client credentials — updated ciphertext persists server-side only.
            </p>
            {oauthInlineErr ? (
              <p className="rounded-xl border border-danger/35 bg-black/65 px-3 py-2 text-sm text-danger" role="alert">
                {oauthInlineErr}
              </p>
            ) : null}
            <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
              Connector slug
              <input
                value={refreshSlug}
                onChange={(e) => setRefreshSlug(e.target.value)}
                className="qs-input min-h-[44px] font-mono text-sm"
                placeholder="outlook_graph"
                required
              />
            </label>
            <button
              type="submit"
              disabled={oauthBusy}
              className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-2xl border border-pollen/45 px-4 py-3 font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen hover:bg-pollen/10 disabled:opacity-40 touch-manipulation"
            >
              {oauthBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : null}
              Refresh OAuth token
            </button>
          </form>

          <form onSubmit={(e) => void runProbe(e)} className="v4-learning-panel space-y-4">
            <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#EEEEFF]">Egress probe (vault GET)</h3>
            <p className="font-[family-name:var(--font-poppins)] text-xs text-(--qs-text-3)">
              Applies vaulted bearer headers then performs <span className="font-mono text-cyan">GET</span> with retry policy — HTTPS only.
            </p>
            <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
              Vault slug for Authorization
              <input
                value={probeSlug}
                onChange={(e) => setProbeSlug(e.target.value)}
                className="qs-input min-h-[44px] font-mono text-sm"
                required
              />
            </label>
            <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs font-medium text-[#BEBED6]">
              HTTPS URL
              <input
                value={probeUrl}
                onChange={(e) => setProbeUrl(e.target.value)}
                className="qs-input min-h-[44px] font-mono text-xs"
                placeholder="https://api.github.com/user"
                required
              />
            </label>
            <button
              type="submit"
              disabled={probeBusy}
              className="qs-btn qs-btn--ghost w-full touch-manipulation"
            >
              {probeBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : null}
              Run HTTPS probe
            </button>
            {probeInlineErr ? (
              <p className="rounded-xl border border-danger/35 bg-black/65 px-3 py-2 text-sm text-danger" role="alert">
                {probeInlineErr}
              </p>
            ) : null}
            {probeInlineOk ? (
              <p className="rounded-xl border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-200" role="status">
                {probeInlineOk}
              </p>
            ) : null}
          </form>
        </div>
      </div>
    </V4Card>
  );
}
