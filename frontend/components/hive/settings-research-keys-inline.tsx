"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePutJson } from "@/lib/api";

type ResearchProvider = "tavily" | "serper";

interface ProviderStatus {
  configured: boolean;
  masked: string | null;
}

interface ResearchStatusResponse {
  providers: Record<ResearchProvider, ProviderStatus>;
}

const RESEARCH_ROWS: readonly {
  id: ResearchProvider;
  label: string;
  hint: string;
  docs: string;
}[] = [
  {
    id: "tavily",
    label: "Tavily Search",
    hint: "Optional — improves researcher web search in supervisor sessions.",
    docs: "https://tavily.com",
  },
  {
    id: "serper",
    label: "Serper (Google JSON)",
    hint: "Optional paid Google-lite JSON search for Research bees.",
    docs: "https://serper.dev",
  },
];

export function SettingsResearchKeysInline(): JSX.Element {
  const [status, setStatus] = useState<ResearchStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyProvider, setBusyProvider] = useState<ResearchProvider | null>(null);
  const [drafts, setDrafts] = useState<Record<ResearchProvider, string>>({ tavily: "", serper: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const body = await hiveGet<ResearchStatusResponse>("external-apis/research-keys/status");
      setStatus(body);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Could not load research keys");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const saveKey = useCallback(
    async (provider: ResearchProvider) => {
      const apiKey = drafts[provider].trim();
      if (apiKey.length < 8) {
        toast.error("API key is too short.");
        return;
      }
      setBusyProvider(provider);
      try {
        await hivePutJson(`external-apis/research-keys/${provider}`, { api_key: apiKey });
        toast.success(`${provider === "tavily" ? "Tavily" : "Serper"} key saved.`);
        setDrafts((prev) => ({ ...prev, [provider]: "" }));
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Could not save research key");
      } finally {
        setBusyProvider(null);
      }
    },
    [drafts, load],
  );

  const removeKey = useCallback(
    async (provider: ResearchProvider) => {
      setBusyProvider(provider);
      try {
        await hiveDelete(`external-apis/research-keys/${provider}`);
        toast.message("Vault key removed — env fallback may still apply.");
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Could not remove research key");
      } finally {
        setBusyProvider(null);
      }
    },
    [load],
  );

  return (
    <V4Card id="research-keys">
      <V4CardHeader
        kicker="Optional"
        title="Research search keys"
        description="Tavily and Serper power Research bee web search. Stored encrypted in your operator vault."
        actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
      />

      <div className="space-y-4">
        {RESEARCH_ROWS.map((row) => {
          const rowStatus = status?.providers[row.id];
          const configured = rowStatus?.configured ?? false;
          const busy = busyProvider === row.id;

          return (
            <div
              key={row.id}
              className="rounded-xl border border-(--qs-border)/60 bg-black/20 p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold text-(--qs-text)">{row.label}</p>
                {configured ? (
                  <V4Badge tone="ok">Configured {rowStatus?.masked ? `· ${rowStatus.masked}` : ""}</V4Badge>
                ) : (
                  <V4Badge tone="info">Not set</V4Badge>
                )}
              </div>
              <p className="mt-1 text-xs text-(--qs-muted)">{row.hint}</p>
              <label htmlFor={`research-key-${row.id}`} className="v4-field-label mt-3">
                API key
              </label>
              <input
                id={`research-key-${row.id}`}
                type="password"
                autoComplete="off"
                className="qs-input mt-1 font-mono text-xs"
                placeholder={configured ? "Paste to rotate key" : "tvly-… or serper-…"}
                value={drafts[row.id]}
                disabled={busy}
                onChange={(e) => setDrafts((prev) => ({ ...prev, [row.id]: e.target.value }))}
              />
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm"
                  disabled={busy || !drafts[row.id].trim()}
                  onClick={() => void saveKey(row.id)}
                >
                  {busy ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : null}
                  Save key
                </button>
                {configured ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm text-danger"
                    disabled={busy}
                    onClick={() => void removeKey(row.id)}
                  >
                    Remove vault key
                  </button>
                ) : null}
                <Link
                  href={row.docs}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                >
                  Get API key →
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </V4Card>
  );
}
