"use client";

import { CpuIcon, Loader2Icon, RefreshCwIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface LocalInferencePing {
  provider: "ollama" | "vllm";
  ok: boolean;
  endpoint: string;
  model_count: number;
  message: string;
}

interface LocalInferenceStatus {
  enabled: boolean;
  llm_airgap: boolean;
  ollama_api_base: string;
  ollama_default_model: string;
  vllm_api_base: string;
  vllm_default_model: string;
  configured_models: string[];
  pings: LocalInferencePing[];
}

/** Settings panel — Ollama/vLLM status + ping (Track M LOC4). */
export function LocalInferencePanel(): JSX.Element | null {
  const [loading, setLoading] = useState(true);
  const [pinging, setPinging] = useState(false);
  const [status, setStatus] = useState<LocalInferenceStatus | null>(null);
  const [disabled, setDisabled] = useState(false);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<LocalInferenceStatus>("llm-routing/local-inference");
      setStatus(body);
      setDisabled(false);
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 404) {
        setDisabled(true);
      } else {
        toast.error(e instanceof HiveApiError ? e.message : "Local inference status unavailable.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const ping = useCallback(async () => {
    setPinging(true);
    try {
      const body = await hivePostJson<LocalInferenceStatus>("llm-routing/local-inference/ping", {});
      setStatus(body);
      const allOk = body.pings.length > 0 && body.pings.every((p) => p.ok);
      toast.success(allOk ? "Local inference reachable." : "Ping finished — see status below.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Ping failed.");
    } finally {
      setPinging(false);
    }
  }, []);

  if (disabled) {
    return null;
  }

  return (
    <V4Card className="v4-card-interactive border-success/25">
      <V4CardHeader
        title="Local Inference · Sovereign LLM"
        description="Ollama/vLLM on your hardware — $0 hops when routing mode is local_sovereign."
        actions={
          status ? (
            <V4Badge tone={status.llm_airgap ? "warn" : status.enabled ? "ok" : "info"}>
              {status.llm_airgap ? "air-gap" : status.enabled ? "enabled" : "off"}
            </V4Badge>
          ) : (
            <CpuIcon className="h-4 w-4 text-success" aria-hidden />
          )
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading local inference…
        </p>
      ) : null}

      {status ? (
        <div className="space-y-4">
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-(--qs-text-3)">Ollama base</dt>
              <dd className="font-mono text-xs text-cyan">{status.ollama_api_base || "—"}</dd>
            </div>
            <div>
              <dt className="text-(--qs-text-3)">Default model</dt>
              <dd className="font-mono text-xs text-pollen">{status.ollama_default_model}</dd>
            </div>
            {status.vllm_api_base ? (
              <div className="sm:col-span-2">
                <dt className="text-(--qs-text-3)">vLLM base</dt>
                <dd className="font-mono text-xs text-cyan">{status.vllm_api_base}</dd>
              </div>
            ) : null}
          </dl>

          {status.configured_models.length > 0 ? (
            <p className="text-xs text-(--qs-text-3)">
              Configured slugs:{" "}
              {status.configured_models.map((m) => (
                <span key={m} className="mr-2 font-mono text-success">
                  {m}
                </span>
              ))}
            </p>
          ) : null}

          {status.pings.length > 0 ? (
            <ul className="space-y-2 text-sm">
              {status.pings.map((p) => (
                <li
                  key={p.provider}
                  className={`rounded-md border px-3 py-2 ${p.ok ? "border-success/30 bg-success/5" : "border-error/30 bg-error/5"}`}
                >
                  <span className="font-medium capitalize">{p.provider}</span>
                  <span className="ml-2 text-(--qs-text-3)">{p.message}</span>
                </li>
              ))}
            </ul>
          ) : null}

          <button
            type="button"
            disabled={pinging}
            onClick={() => void ping()}
            className="inline-flex items-center gap-2 rounded-md border border-success/40 px-3 py-2 text-sm text-success hover:bg-success/10 disabled:opacity-50"
          >
            {pinging ? (
              <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <RefreshCwIcon className="h-4 w-4" aria-hidden />
            )}
            Ping Ollama / vLLM
          </button>

          {status.llm_airgap ? (
            <p className="text-xs text-magenta">
              LLM_AIRGAP=1 — cloud hops are hard-blocked. Use local_sovereign routing only.
            </p>
          ) : null}
        </div>
      ) : null}
    </V4Card>
  );
}
