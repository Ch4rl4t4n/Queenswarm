"use client";

import Link from "next/link";
import { Loader2, Radar } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import {
  applySoloBootstrap,
  fetchBootstrapChecklist,
  fetchVirtualCompanyProfile,
  saveVirtualCompanyProfile,
  type BootstrapChecklist,
  type VirtualCompanyProfile,
} from "@/lib/virtual-company-api";

const FOCUS_OPTIONS = [
  "marketing",
  "sales",
  "finance",
  "digital",
  "product",
  "technology",
  "geopolitics",
  "automation",
] as const;

interface VirtualCompanyProfilePanelProps {
  onProfileChange?: (profile: VirtualCompanyProfile) => void;
}

/** Operator profile + free-first bootstrap for Virtual Company swarms. */
export function VirtualCompanyProfilePanel({ onProfileChange }: VirtualCompanyProfilePanelProps): JSX.Element {
  const [profile, setProfile] = useState<VirtualCompanyProfile | null>(null);
  const [checklist, setChecklist] = useState<BootstrapChecklist | null>(null);
  const [busy, setBusy] = useState(false);
  const [bootBusy, setBootBusy] = useState(false);

  const reload = useCallback(async (): Promise<void> => {
    const [p, c] = await Promise.all([fetchVirtualCompanyProfile(), fetchBootstrapChecklist()]);
    setProfile(p);
    setChecklist(c);
    onProfileChange?.(p);
  }, [onProfileChange]);

  useEffect(() => {
    void reload().catch(() => {
      /* non-fatal on first load */
    });
  }, [reload]);

  const save = async (): Promise<void> => {
    if (!profile) {
      return;
    }
    setBusy(true);
    try {
      const saved = await saveVirtualCompanyProfile({
        brand_name: profile.brand_name,
        industry: profile.industry,
        focus_areas: profile.focus_areas,
        risk_tolerance: profile.risk_tolerance,
        primary_goal: profile.primary_goal,
      });
      setProfile(saved);
      onProfileChange?.(saved);
      await reload();
      toast.success("Profile saved — swarms will inherit this context");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const bootstrap = async (): Promise<void> => {
    setBootBusy(true);
    try {
      const result = await applySoloBootstrap();
      setChecklist(result.checklist);
      toast.success(
        result.routing.changed ? "Solo bootstrap: free_first routing enabled" : "Solo bootstrap already active",
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Bootstrap failed");
    } finally {
      setBootBusy(false);
    }
  };

  if (!profile) {
    return (
      <V4Card className="flex items-center gap-2 p-4">
        <Loader2 className="h-4 w-4 animate-spin text-pollen" aria-hidden />
        <span className="text-xs text-(--qs-text-3)">Loading Virtual Company profile…</span>
      </V4Card>
    );
  }

  return (
    <V4Card className="mb-6">
      <V4CardHeader
        title="Virtual Company profile"
        description="Brand + goals flow into every department swarm and supervisor session (free-first, simulate default)."
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-xs">
          <span className="text-(--qs-text-3)">Brand / project name</span>
          <input
            className="qs-input mt-1 w-full"
            value={profile.brand_name}
            onChange={(e) => setProfile({ ...profile, brand_name: e.target.value })}
            placeholder="Queenswarm / your brand"
          />
        </label>
        <label className="block text-xs">
          <span className="text-(--qs-text-3)">Industry</span>
          <input
            className="qs-input mt-1 w-full"
            value={profile.industry}
            onChange={(e) => setProfile({ ...profile, industry: e.target.value })}
            placeholder="SaaS, e-commerce, agency…"
          />
        </label>
        <label className="col-span-full block text-xs">
          <span className="text-(--qs-text-3)">Primary goal (1–2 sentences)</span>
          <textarea
            className="qs-input mt-1 min-h-[72px] w-full"
            value={profile.primary_goal}
            onChange={(e) => setProfile({ ...profile, primary_goal: e.target.value })}
            placeholder="What should the hive optimize for this quarter?"
          />
        </label>
        <fieldset className="col-span-full text-xs">
          <legend className="text-(--qs-text-3)">Focus areas</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {FOCUS_OPTIONS.map((area) => {
              const active = profile.focus_areas.includes(area);
              return (
                <button
                  key={area}
                  type="button"
                  className={`rounded-full border px-2 py-0.5 text-[11px] ${active ? "border-pollen/50 bg-pollen/15 text-pollen" : "border-(--qs-border) text-(--qs-text-3)"}`}
                  onClick={() =>
                    setProfile({
                      ...profile,
                      focus_areas: active
                        ? profile.focus_areas.filter((x) => x !== area)
                        : [...profile.focus_areas, area],
                    })
                  }
                >
                  {area}
                </button>
              );
            })}
          </div>
        </fieldset>
        <label className="block text-xs">
          <span className="text-(--qs-text-3)">Risk tolerance (live execution)</span>
          <select
            className="qs-input mt-1 w-full"
            value={profile.risk_tolerance}
            onChange={(e) =>
              setProfile({
                ...profile,
                risk_tolerance: e.target.value as VirtualCompanyProfile["risk_tolerance"],
              })
            }
          >
            <option value="low">Low — always approve live</option>
            <option value="medium">Medium</option>
            <option value="high">High — still requires ES policy</option>
          </select>
        </label>
      </div>

      {checklist ? (
        <div className="mt-4 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-xs text-(--qs-text-2)">
          <div className="flex flex-wrap items-center gap-2">
            <Radar className="h-3.5 w-3.5 text-cyan" aria-hidden />
            <span>
              Connectors ready: {checklist.departments_ready}/{checklist.departments_total} departments · LLM{" "}
              <V4Badge tone={checklist.free_first_active ? "ok" : "warn"}>{checklist.routing_mode}</V4Badge>
            </span>
          </div>
          <ul className="mt-2 list-inside list-disc text-[11px] text-(--qs-text-3)">
            {checklist.next_steps.slice(0, 4).map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={busy} onClick={() => void save()}>
          {busy ? "Saving…" : "Save profile"}
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm"
          disabled={bootBusy}
          onClick={() => void bootstrap()}
        >
          {bootBusy ? "Bootstrapping…" : "Apply solo free_first"}
        </button>
        <Link href="/integrations?tab=studio" className="qs-btn qs-btn--ghost qs-btn--sm">
          Execution Studio
        </Link>
        <Link href="/settings/costs" className="qs-btn qs-btn--ghost qs-btn--sm">
          LLM routing
        </Link>
      </div>
    </V4Card>
  );
}
