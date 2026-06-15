"use client";

import { Loader2, Shield } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson } from "@/lib/api";

interface LoopGuardrailsPolicy {
  enabled: boolean;
  max_turns: number;
  min_score: number;
  cost_cap_usd: number;
  cost_warn_ratio: number;
  source: "deployment" | "tenant";
}

export function LoopGuardrailsPanel(): JSX.Element | null {
  const [policy, setPolicy] = useState<LoopGuardrailsPolicy | null>(null);
  const [draft, setDraft] = useState<LoopGuardrailsPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<LoopGuardrailsPolicy>("solo-operator/loop-guardrails");
      setPolicy(data);
      setDraft(data);
    } catch {
      setPolicy(null);
      setDraft(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(async () => {
    if (!draft) {
      return;
    }
    setSaving(true);
    try {
      const data = await hivePatchJson<LoopGuardrailsPolicy>("solo-operator/loop-guardrails", {
        enabled: draft.enabled,
        max_turns: draft.max_turns,
        min_score: draft.min_score,
        cost_cap_usd: draft.cost_cap_usd,
        cost_warn_ratio: draft.cost_warn_ratio,
      });
      setPolicy(data);
      setDraft(data);
      toast.success("Loop guardrails saved.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [draft]);

  if (loading) {
    return (
      <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading loop guardrails…
      </V4Card>
    );
  }

  if (!draft) {
    return null;
  }

  const minScoreLabel = `${(draft.min_score * 5).toFixed(1)}/5`;

  return (
    <V4Card id="harness-loops-guardrails" className="border-cyan-500/25">
      <V4CardHeader
        kicker="LOOP2 · Closed loops"
        title="Loop guardrails"
        description="Max turns, min rubric score, and session cost cap — applied to every new supervisor session (except Queen Maintainer)."
        actions={
          <div className="flex items-center gap-2">
            <V4Badge tone={draft.enabled ? "ok" : "warn"}>{draft.enabled ? "Active" : "Off"}</V4Badge>
            <HiveRefreshButton busy={loading} onClick={() => void load()} />
          </div>
        }
      />
      <div className="space-y-4 px-4 pb-4">
        <label className="flex items-center gap-2 text-sm text-white/80">
          <input
            type="checkbox"
            checked={draft.enabled}
            onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
          />
          Enable closed-loop guardrails on new sessions
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="text-white/60">Max turns</span>
            <input
              type="number"
              min={1}
              max={25}
              className="qs-input mt-1 w-full font-mono"
              value={draft.max_turns}
              onChange={(e) => setDraft({ ...draft, max_turns: Number(e.target.value) })}
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Min rubric score ({minScoreLabel})</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              className="mt-2 w-full"
              value={draft.min_score}
              onChange={(e) => setDraft({ ...draft, min_score: Number(e.target.value) })}
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Session cost cap (USD)</span>
            <input
              type="number"
              min={0.05}
              max={50}
              step={0.05}
              className="qs-input mt-1 w-full font-mono"
              value={draft.cost_cap_usd}
              onChange={(e) => setDraft({ ...draft, cost_cap_usd: Number(e.target.value) })}
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Cost warn ratio</span>
            <input
              type="number"
              min={0.1}
              max={1}
              step={0.05}
              className="qs-input mt-1 w-full font-mono"
              value={draft.cost_warn_ratio}
              onChange={(e) => setDraft({ ...draft, cost_warn_ratio: Number(e.target.value) })}
            />
          </label>
        </div>
        <p className="text-xs text-white/50">
          Source: {policy?.source ?? draft.source}. Queen Maintainer sessions keep their own economy caps.
        </p>
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm inline-flex gap-1.5"
          disabled={saving}
          onClick={() => void save()}
        >
          {saving ? <Loader2 className="size-4 animate-spin" /> : <Shield className="size-4" />}
          Save guardrails
        </button>
      </div>
    </V4Card>
  );
}
