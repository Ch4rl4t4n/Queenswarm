"use client";

import Link from "next/link";
import { AlertTriangleIcon, CheckCircle2Icon, Loader2Icon, ZapIcon } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { QsSelect } from "@/components/ui/qs-select";
import { HiveApiError, hivePostJson, hivePutJson } from "@/lib/api";
import { MANUAL_HREFS } from "@/lib/manual-routes";
import { cn } from "@/lib/utils";

export interface FactoryLlmOption {
  value: string;
  label: string;
  configured: boolean;
}

export interface FactoryLlmReadiness {
  grok_configured: boolean;
  anthropic_configured: boolean;
  openai_configured: boolean;
  openrouter_configured?: boolean;
  chain_usable: boolean;
  build_allowed: boolean;
  grok_primary?: boolean;
  openrouter_primary?: boolean;
  primary_model: string;
  recommended_action: string;
  decomposition_chain: string[];
  available_models?: FactoryLlmOption[];
  smoke_ok: boolean | null;
  smoke_error: string | null;
}

interface FactoryLlmReadinessBannerProps {
  llm: FactoryLlmReadiness | null | undefined;
  onSmoked?: (next: FactoryLlmReadiness) => void;
  className?: string;
}

function primaryLabel(status: FactoryLlmReadiness): string {
  const match = status.available_models?.find((row) => row.value === status.primary_model);
  if (match?.label) {
    return match.label;
  }
  if (status.openrouter_primary) {
    return "Nemotron (OpenRouter)";
  }
  if (status.grok_primary) {
    return "Grok (xAI)";
  }
  return status.primary_model || "Factory LLM";
}

function providerBadges(status: FactoryLlmReadiness): string[] {
  const badges: string[] = [];
  if (status.openrouter_configured) {
    badges.push(status.openrouter_primary ? "OpenRouter ✓ primary" : "OpenRouter ✓");
  }
  if (status.grok_configured) {
    badges.push(status.grok_primary ? "Grok ✓ primary" : "Grok ✓");
  }
  if (status.openai_configured) {
    badges.push("OpenAI ✓");
  }
  if (status.anthropic_configured) {
    badges.push("Anthropic ✓");
  }
  return badges;
}

export function FactoryLlmReadinessBanner({
  llm,
  onSmoked,
  className,
}: FactoryLlmReadinessBannerProps): JSX.Element | null {
  const [smokeBusy, setSmokeBusy] = useState(false);
  const [modelBusy, setModelBusy] = useState(false);
  const [local, setLocal] = useState<FactoryLlmReadiness | null>(null);

  const status = local ?? llm;

  const modelOptions = useMemo(() => {
    if (!status?.available_models?.length) {
      return status?.primary_model
        ? [{ value: status.primary_model, label: status.primary_model, configured: true }]
        : [];
    }
    return status.available_models.map((row) => ({
      value: row.value,
      label: row.configured ? row.label : `${row.label} (key missing)`,
      disabled: !row.configured,
    }));
  }, [status]);

  const runSmoke = useCallback(async () => {
    setSmokeBusy(true);
    try {
      const next = await hivePostJson<FactoryLlmReadiness>("factory-readiness/llm/smoke", {});
      setLocal(next);
      onSmoked?.(next);
      if (next.smoke_ok) {
        toast.success(`${primaryLabel(next)} smoke test passed — factory builds allowed.`);
      } else {
        toast.error(next.smoke_error ?? next.recommended_action ?? "Smoke test failed.");
      }
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Smoke test request failed.");
    } finally {
      setSmokeBusy(false);
    }
  }, [onSmoked]);

  const savePrimaryModel = useCallback(
    async (primaryModel: string) => {
      if (!status || primaryModel === status.primary_model) {
        return;
      }
      setModelBusy(true);
      try {
        const next = await hivePutJson<FactoryLlmReadiness>("factory-readiness/llm/primary", {
          primary_model: primaryModel,
        });
        setLocal(next);
        onSmoked?.(next);
        toast.success(`Factory LLM set to ${primaryLabel(next)}. Run smoke test before Build.`);
      } catch (err) {
        toast.error(err instanceof HiveApiError ? err.message : "Could not save factory LLM.");
      } finally {
        setModelBusy(false);
      }
    },
    [onSmoked, status],
  );

  if (!status) {
    return null;
  }

  const ready = status.build_allowed && status.chain_usable;
  const smokeFailed = status.smoke_ok === false;
  const smokePassed = status.smoke_ok === true;
  const selectedConfigured =
    status.available_models?.find((row) => row.value === status.primary_model)?.configured ?? ready;

  if (ready && smokePassed) {
    return (
      <div
        className={cn(
          "flex flex-col gap-3 rounded-xl border border-(--qs-success)/30 bg-(--qs-success)/5 px-4 py-3 text-sm",
          className,
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-2 text-(--qs-success)">
            <CheckCircle2Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
            <div>
              <p className="font-medium">{primaryLabel(status)} ready for factory builds</p>
              <p className="text-xs text-white/60">
                {status.decomposition_chain.join(" → ") || "Decomposition chain configured."}
              </p>
            </div>
          </div>
          {modelOptions.length > 0 ? (
            <label className="min-w-[14rem] flex-1 space-y-1 text-xs sm:max-w-xs">
              <span className="text-white/60">Factory LLM</span>
              <QsSelect
                value={status.primary_model}
                options={modelOptions}
                onValueChange={(value) => void savePrimaryModel(value)}
                disabled={modelBusy}
              />
            </label>
          ) : null}
        </div>
      </div>
    );
  }

  const tone = ready ? "warn" : "error";
  const borderClass =
    tone === "error" ? "border-(--qs-danger)/40 bg-(--qs-danger)/5" : "border-pollen/30 bg-pollen/5";
  const textClass = tone === "error" ? "text-(--qs-danger)" : "text-pollen";

  const headline = !ready
    ? !selectedConfigured
      ? "Factory builds blocked — selected LLM not routable"
      : "Factory builds blocked — LLM not configured"
    : !selectedConfigured
      ? "Selected LLM missing credentials — add key or pick another model"
      : `${primaryLabel(status)} configured — run smoke test`;

  return (
    <div className={cn("flex flex-col gap-3 rounded-xl border px-4 py-3 text-sm", borderClass, className)}>
      <div className="flex flex-wrap items-start gap-3">
        <AlertTriangleIcon className={cn("mt-0.5 size-4 shrink-0", textClass)} aria-hidden />
        <div className="min-w-0 flex-1">
          <p className={cn("font-medium", textClass)}>{headline}</p>
          <p className="mt-1 text-xs text-white/70">{status.recommended_action}</p>
          {smokeFailed && status.smoke_error ? (
            <p className="mt-1 font-mono text-xs text-(--qs-danger)">{status.smoke_error}</p>
          ) : null}
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-white/50">
            {providerBadges(status).map((badge) => (
              <span key={badge}>{badge}</span>
            ))}
          </div>
        </div>
        {modelOptions.length > 0 ? (
          <label className="min-w-[14rem] flex-1 space-y-1 text-xs sm:max-w-xs">
            <span className="text-white/60">Factory LLM</span>
            <QsSelect
              value={status.primary_model}
              options={modelOptions}
              onValueChange={(value) => void savePrimaryModel(value)}
              disabled={modelBusy}
            />
          </label>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2">
        <Link href={MANUAL_HREFS.settingsLlmKeys} className="qs-btn qs-btn--primary qs-btn--sm">
          LLM keys
        </Link>
        {ready ? (
          <button
            type="button"
            className="qs-btn qs-btn--secondary qs-btn--sm gap-1"
            disabled={smokeBusy || modelBusy}
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
