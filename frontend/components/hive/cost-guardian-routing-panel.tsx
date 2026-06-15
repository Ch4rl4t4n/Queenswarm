"use client";

import { Loader2Icon, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { usePlatform } from "@/components/hive/platform-context";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePutJson } from "@/lib/api";

type RoutingMode = "quality" | "economy" | "free_first" | "local_sovereign";

interface LlmRoutingSettings {
  routing_mode: RoutingMode;
  cost_guardian_enabled: boolean;
  auto_upgrade_on_failure: boolean;
  feature_enabled: boolean;
  quality_primary_model: string;
  economy_primary_model: string;
  local_llm_enabled?: boolean;
  llm_airgap?: boolean;
  ollama_default_model?: string;
  configured_local_models?: string[];
}

const BASE_ROUTING_OPTIONS: { value: RoutingMode; label: string }[] = [
  { value: "quality", label: "Quality first (Grok → Claude → GPT-4o mini)" },
  { value: "economy", label: "Economy (GPT-4o mini → Claude → Grok)" },
  { value: "free_first", label: "Free-first (cheap hop, auto-upgrade on failure)" },
];

const LOCAL_SOVEREIGN_OPTION = {
  value: "local_sovereign" as const,
  label: "Local sovereign (Ollama / vLLM only — $0)",
};

/** Settings panel — LiteLLM routing mode + Cost Guardian auto-upgrade. */
export function CostGuardianRoutingPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [settings, setSettings] = useState<LlmRoutingSettings | null>(null);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<LlmRoutingSettings>("llm-routing/settings");
      setSettings(body);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Routing settings unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(
    async (patch: Partial<LlmRoutingSettings>) => {
      if (!settings) return;
      setBusy(true);
      try {
        const body = await hivePutJson<LlmRoutingSettings>("llm-routing/settings", {
          routing_mode: patch.routing_mode ?? settings.routing_mode,
          cost_guardian_enabled: patch.cost_guardian_enabled ?? settings.cost_guardian_enabled,
          auto_upgrade_on_failure: patch.auto_upgrade_on_failure ?? settings.auto_upgrade_on_failure,
        });
        setSettings(body);
        toast.success("Routing settings saved.");
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Save failed.");
      } finally {
        setBusy(false);
      }
    },
    [settings],
  );

  const routingOptions = useMemo(() => {
    const opts = [...BASE_ROUTING_OPTIONS];
    if (settings?.local_llm_enabled) {
      opts.push(LOCAL_SOVEREIGN_OPTION);
    }
    return opts;
  }, [settings?.local_llm_enabled]);

  if (!hasFeature("free_first_routing")) {
    return null;
  }

  return (
    <V4Card className="v4-card-interactive border-cyan/25">
      <V4CardHeader
        title="Cost Guardian · LLM routing"
        description="Free-First mode routes simple hops to cheaper models, then auto-upgrades on failure."
        actions={
          settings ? (
            <V4Badge tone={settings.routing_mode === "quality" ? "info" : "ok"}>{settings.routing_mode}</V4Badge>
          ) : (
            <ShieldCheck className="h-4 w-4 text-cyan" aria-hidden />
          )
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading routing…
        </p>
      ) : null}

      {settings ? (
        <div className="space-y-4">
          <label className="block space-y-2 text-sm">
            <span className="text-(--qs-text-2)">Routing mode</span>
            <QsSelect
              value={settings.routing_mode}
              options={routingOptions.map((o) => ({ value: o.value, label: o.label }))}
              onValueChange={(value) => void save({ routing_mode: value as RoutingMode })}
              disabled={busy}
            />
          </label>

          <label className="flex items-center justify-between gap-3 text-sm">
            <span className="text-(--qs-text-2)">Cost Guardian enabled</span>
            <input
              type="checkbox"
              checked={settings.cost_guardian_enabled}
              disabled={busy}
              onChange={(e) => void save({ cost_guardian_enabled: e.target.checked })}
              className="h-4 w-4 accent-pollen"
            />
          </label>

          <label className="flex items-center justify-between gap-3 text-sm">
            <span className="text-(--qs-text-2)">Auto-upgrade on failure</span>
            <input
              type="checkbox"
              checked={settings.auto_upgrade_on_failure}
              disabled={busy || !settings.cost_guardian_enabled}
              onChange={(e) => void save({ auto_upgrade_on_failure: e.target.checked })}
              className="h-4 w-4 accent-pollen"
            />
          </label>

          <p className="text-xs text-(--qs-text-3)">
            Quality primary: <span className="font-mono text-cyan">{settings.quality_primary_model}</span> · Economy
            hop: <span className="font-mono text-pollen">{settings.economy_primary_model}</span>
            {settings.local_llm_enabled && settings.ollama_default_model ? (
              <>
                {" "}
                · Local: <span className="font-mono text-success">{settings.ollama_default_model}</span>
              </>
            ) : null}
          </p>
          {settings.llm_airgap ? (
            <p className="text-xs text-magenta">LLM_AIRGAP active — cloud models are blocked at runtime.</p>
          ) : null}
        </div>
      ) : null}
    </V4Card>
  );
}
