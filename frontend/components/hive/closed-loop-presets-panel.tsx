"use client";

import { Check, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface LoopPreset {
  preset_id: string;
  label: string;
  description: string;
  lane: string;
  rubric_template_id: string;
  max_turns: number;
  min_score: number;
  simulate_only: boolean;
  href: string;
}

interface PresetsSnapshot {
  enabled: boolean;
  presets: LoopPreset[];
  active_preset_id: string | null;
  active_rubric_template_id: string | null;
}

interface ApplyResponse {
  ok: boolean;
  preset_id: string;
  label: string;
  message: string;
}

export function ClosedLoopPresetsPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<PresetsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<PresetsSnapshot>("solo-operator/closed-loop-presets");
      setSnapshot(data);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const applyPreset = useCallback(
    async (presetId: string) => {
      setApplying(presetId);
      try {
        const data = await hivePostJson<ApplyResponse>("solo-operator/closed-loop-presets/apply", {
          preset_id: presetId,
        });
        toast.success(data.message || `Applied ${data.label}`);
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Apply failed");
      } finally {
        setApplying(null);
      }
    },
    [load],
  );

  if (loading) {
    return (
      <V4Card className="mt-4 flex items-center gap-2 p-4 text-sm text-white/60">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading closed-loop presets…
      </V4Card>
    );
  }

  if (!snapshot?.enabled || snapshot.presets.length === 0) {
    return null;
  }

  return (
    <V4Card id="harness-closed-loop-presets" className="mt-4 border-magenta-500/25">
      <V4CardHeader
        kicker="LOOP5 · Presets"
        title="Closed-loop presets"
        description="One-click LOOP2 guardrails + default rubric for Factory, social intel, publish/SEO bulk."
        actions={
          <HiveRefreshButton busy={loading} onClick={() => void load()} />
        }
      />
      <ul className="space-y-3 px-4 pb-4">
        {snapshot.presets.map((preset) => {
          const active = snapshot.active_preset_id === preset.preset_id;
          const minLabel = `${(preset.min_score * 5).toFixed(1)}/5`;
          return (
            <li
              key={preset.preset_id}
              className="rounded border border-white/10 bg-white/[0.03] p-3 text-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-white">{preset.label}</span>
                    {active ? <V4Badge tone="ok">Active</V4Badge> : null}
                    {preset.simulate_only ? <V4Badge tone="warn">Simulate-only</V4Badge> : null}
                  </div>
                  <p className="mt-1 text-white/60">{preset.description}</p>
                  <p className="mt-1 font-mono text-xs text-white/40">
                    {preset.rubric_template_id} · {preset.max_turns} turns · min {minLabel}
                  </p>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row">
                  {preset.href ? (
                    <Link href={preset.href} className="qs-btn qs-btn--ghost qs-btn--sm">
                      Open lane
                    </Link>
                  ) : null}
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm inline-flex gap-1"
                    disabled={applying === preset.preset_id}
                    onClick={() => void applyPreset(preset.preset_id)}
                  >
                    {applying === preset.preset_id ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : active ? (
                      <Check className="size-4" />
                    ) : (
                      <Sparkles className="size-4" />
                    )}
                    {active ? "Re-apply" : "Apply"}
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </V4Card>
  );
}
