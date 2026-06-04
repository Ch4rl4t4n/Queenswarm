"use client";

import Link from "next/link";
import { AlertTriangleIcon, CheckCircle2Icon, Loader2Icon, ZapIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hivePostJson } from "@/lib/api";
import { MANUAL_HREFS } from "@/lib/manual-routes";
import { cn } from "@/lib/utils";

export interface FactoryLlmReadiness {
  grok_configured: boolean;
  anthropic_configured: boolean;
  openai_configured: boolean;
  chain_usable: boolean;
  build_allowed: boolean;
  grok_primary?: boolean;
  recommended_action: string;
  decomposition_chain: string[];
  smoke_ok: boolean | null;
  smoke_error: string | null;
}

interface FactoryLlmReadinessBannerProps {
  llm: FactoryLlmReadiness | null | undefined;
  onSmoked?: (next: FactoryLlmReadiness) => void;
  className?: string;
}

export function FactoryLlmReadinessBanner({
  llm,
  onSmoked,
  className,
}: FactoryLlmReadinessBannerProps): JSX.Element | null {
  const [smokeBusy, setSmokeBusy] = useState(false);
  const [local, setLocal] = useState<FactoryLlmReadiness | null>(null);

  const status = local ?? llm;

  const runSmoke = useCallback(async () => {
    setSmokeBusy(true);
    try {
      const next = await hivePostJson<FactoryLlmReadiness>("factory-readiness/llm/smoke", {});
      setLocal(next);
      onSmoked?.(next);
      if (next.smoke_ok) {
        toast.success("Grok smoke test passed — factory builds allowed.");
      } else {
        toast.error(next.smoke_error ?? next.recommended_action ?? "Smoke test failed.");
      }
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Smoke test request failed.");
    } finally {
      setSmokeBusy(false);
    }
  }, [onSmoked]);

  if (!status) {
    return null;
  }

  const grokFirst = status.grok_primary !== false && status.grok_configured;
  const ready = status.build_allowed && status.chain_usable;
  const smokeFailed = status.smoke_ok === false;
  const smokePassed = status.smoke_ok === true;

  if (ready && smokePassed) {
    return (
      <div
        className={cn(
          "flex flex-wrap items-center justify-between gap-3 rounded-xl border border-(--qs-success)/30 bg-(--qs-success)/5 px-4 py-3 text-sm",
          className,
        )}
      >
        <div className="flex items-start gap-2 text-(--qs-success)">
          <CheckCircle2Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
          <div>
            <p className="font-medium">{grokFirst ? "Grok ready for factory builds" : "Factory LLM ready"}</p>
            <p className="text-xs text-white/60">
              {status.decomposition_chain.join(" → ") || "Decomposition chain configured."}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const tone = ready ? "warn" : "error";
  const borderClass =
    tone === "error" ? "border-(--qs-danger)/40 bg-(--qs-danger)/5" : "border-pollen/30 bg-pollen/5";
  const textClass = tone === "error" ? "text-(--qs-danger)" : "text-pollen";

  const headline = !ready
    ? grokFirst
      ? "Factory builds blocked — Grok not routable"
      : "Factory builds blocked — LLM not configured"
    : grokFirst
      ? "Grok configured — run smoke test"
      : "LLM credentials present — run smoke test";

  return (
    <div className={cn("flex flex-col gap-3 rounded-xl border px-4 py-3 text-sm", borderClass, className)}>
      <div className="flex items-start gap-2">
        <AlertTriangleIcon className={cn("mt-0.5 size-4 shrink-0", textClass)} aria-hidden />
        <div className="min-w-0 flex-1">
          <p className={cn("font-medium", textClass)}>{headline}</p>
          <p className="mt-1 text-xs text-white/70">{status.recommended_action}</p>
          {smokeFailed && status.smoke_error ? (
            <p className="mt-1 font-mono text-xs text-(--qs-danger)">{status.smoke_error}</p>
          ) : null}
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-white/50">
            <span>Grok {status.grok_configured ? "✓ primary" : "—"}</span>
            {!grokFirst && status.openai_configured ? <span>OpenAI ✓</span> : null}
            {!grokFirst && status.anthropic_configured ? <span>Anthropic ✓</span> : null}
          </div>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Link href={MANUAL_HREFS.settingsLlmKeys} className="qs-btn qs-btn--primary qs-btn--sm">
          Grok / LLM keys
        </Link>
        {ready ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
            disabled={smokeBusy}
            onClick={() => void runSmoke()}
          >
            {smokeBusy ? <Loader2Icon className="size-3.5 animate-spin" /> : <ZapIcon className="size-3.5" />}
            Run smoke test
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function factoryBuildDisabled(llm: FactoryLlmReadiness | null | undefined): boolean {
  if (!llm) {
    return false;
  }
  return !(llm.build_allowed && llm.chain_usable);
}
