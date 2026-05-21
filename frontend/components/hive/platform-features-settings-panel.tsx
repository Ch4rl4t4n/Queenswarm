"use client";

import { Loader2Icon, RotateCcwIcon } from "lucide-react";
import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { usePlatform } from "@/components/hive/platform-context";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface PlatformFeatureMatrixCell {
  enabled: boolean;
  source: "default" | "override";
  default_enabled: boolean;
}

export interface PlatformFeatureMatrixRow {
  section_id: string;
  section_label: string;
  section_tone: string;
  feature_key: string;
  label: string;
  cells: Record<string, PlatformFeatureMatrixCell>;
}

export interface PlatformFeatureProfileColumn {
  key: string;
  label: string;
  description: string;
  tone: string;
}

export interface PlatformFeatureMatrixPayload {
  profiles: PlatformFeatureProfileColumn[];
  rows: PlatformFeatureMatrixRow[];
}

interface PlatformFeaturePreviewPayload {
  profile_key: string;
  platform_mode: string;
  subscription_tier: string;
  is_admin: boolean;
  enabled_count: number;
  disabled_count: number;
  enabled_features: string[];
  disabled_features: string[];
}

const PREVIEW_PROFILES = ["internal", "commercial_free", "commercial_pro", "commercial_enterprise"] as const;

const PREVIEW_PROFILE_OPTIONS = PREVIEW_PROFILES.map((profile) => ({
  value: profile,
  label: profile.replaceAll("_", " · "),
}));

const TONE_STYLES: Record<string, { section: string; header: string }> = {
  cyan: {
    section: "border-cyan/35 bg-cyan/[0.06] text-cyan",
    header: "text-cyan border-cyan/30",
  },
  amber: {
    section: "border-pollen/35 bg-pollen/[0.06] text-pollen",
    header: "text-pollen border-pollen/30",
  },
  pollen: {
    section: "border-pollen/35 bg-pollen/[0.06] text-pollen",
    header: "text-pollen border-pollen/30",
  },
  magenta: {
    section: "border-[#FF00AA]/35 bg-[#FF00AA]/[0.06] text-[#FF00AA]",
    header: "text-[#FF00AA] border-[#FF00AA]/30",
  },
  green: {
    section: "border-[#00FF88]/35 bg-[#00FF88]/[0.06] text-[#00FF88]",
    header: "text-[#00FF88] border-[#00FF88]/30",
  },
  purple: {
    section: "border-purple-400/35 bg-purple-400/[0.06] text-purple-300",
    header: "text-purple-300 border-purple-400/30",
  },
  zinc: {
    section: "border-zinc-500/35 bg-zinc-500/[0.06] text-zinc-300",
    header: "text-zinc-300 border-zinc-500/30",
  },
  red: {
    section: "border-[#FF3366]/35 bg-[#FF3366]/[0.06] text-[#FF3366]",
    header: "text-[#FF3366] border-[#FF3366]/30",
  },
};

function toneStyle(tone: string, kind: "section" | "header"): string {
  return TONE_STYLES[tone]?.[kind] ?? TONE_STYLES.zinc[kind];
}

function profileHeaderStyle(tone: string): string {
  const map: Record<string, string> = {
    cyan: "text-cyan",
    amber: "text-pollen",
    green: "text-[#00FF88]",
    purple: "text-purple-300",
    zinc: "text-zinc-400",
  };
  return map[tone] ?? "text-(--qs-text-2)";
}

export function PlatformFeaturesSettingsPanel() {
  const { isAdmin, platformMode, refresh } = usePlatform();
  const [matrix, setMatrix] = useState<PlatformFeatureMatrixPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [resettingProfile, setResettingProfile] = useState<string | null>(null);
  const [previewProfile, setPreviewProfile] = useState<(typeof PREVIEW_PROFILES)[number]>("commercial_pro");
  const [preview, setPreview] = useState<PlatformFeaturePreviewPayload | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const allowed = isAdmin && platformMode === "internal";

  const load = useCallback(async () => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const body = await hiveGet<PlatformFeatureMatrixPayload>("operator/platform-features");
      setMatrix(body);
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Matrix load failed.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [allowed]);

  useEffect(() => {
    void load();
  }, [load]);

  const loadPreview = useCallback(async () => {
    if (!allowed) {
      return;
    }
    setPreviewLoading(true);
    try {
      const body = await hiveGet<PlatformFeaturePreviewPayload>(
        `operator/platform-features/preview?profile_key=${encodeURIComponent(previewProfile)}`,
      );
      setPreview(body);
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Preview failed.";
      toast.error(msg);
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  }, [allowed, previewProfile]);

  useEffect(() => {
    void loadPreview();
  }, [loadPreview]);

  const groupedRows = useMemo(() => {
    if (!matrix) {
      return [];
    }
    const groups: { sectionId: string; sectionLabel: string; sectionTone: string; rows: PlatformFeatureMatrixRow[] }[] = [];
    for (const row of matrix.rows) {
      const last = groups[groups.length - 1];
      if (last && last.sectionId === row.section_id) {
        last.rows.push(row);
      } else {
        groups.push({
          sectionId: row.section_id,
          sectionLabel: row.section_label,
          sectionTone: row.section_tone,
          rows: [row],
        });
      }
    }
    return groups;
  }, [matrix]);

  const patchCell = useCallback(
    async (featureKey: string, profileKey: string, enabled: boolean, revertToDefault = false) => {
      const cellKey = `${featureKey}:${profileKey}`;
      setBusyKey(cellKey);
      try {
        const body = await hivePatchJson<PlatformFeatureMatrixPayload>("operator/platform-features", {
          updates: [
            {
              feature_key: featureKey,
              profile_key: profileKey,
              enabled: revertToDefault ? null : enabled,
            },
          ],
        });
        setMatrix(body);
        await refresh();
        toast.success(revertToDefault ? "Obnovené na predvolenú hodnotu" : "Uložené");
        await loadPreview();
      } catch (error) {
        const msg = error instanceof HiveApiError ? error.message : "Uloženie zlyhalo.";
        toast.error(msg);
        await load();
      } finally {
        setBusyKey(null);
      }
    },
    [load, loadPreview, refresh],
  );

  const resetProfile = useCallback(
    async (profileKey: string) => {
      setResettingProfile(profileKey);
      try {
        const body = await hivePostJson<PlatformFeatureMatrixPayload>(
          `operator/platform-features/reset?profile_key=${encodeURIComponent(profileKey)}`,
          {},
        );
        setMatrix(body);
        await refresh();
        await loadPreview();
        toast.success("Stĺpec resetovaný na katalógové defaulty");
      } catch (error) {
        const msg = error instanceof HiveApiError ? error.message : "Reset zlyhal.";
        toast.error(msg);
      } finally {
        setResettingProfile(null);
      }
    },
    [loadPreview, refresh],
  );

  if (!allowed) {
    return (
      <V4Card>
        <V4CardHeader
          title="Platform features"
          description="Táto sekcia je dostupná len pre admin účet v internal (operator) tenante."
        />
        <p className="px-4 pb-4 text-sm text-(--qs-text-3)">
          Prihlás sa ako admin a prepni na operator workspace.
        </p>
      </V4Card>
    );
  }

  if (loading || !matrix) {
    return (
      <V4Card className="flex min-h-[240px] items-center justify-center">
        <Loader2Icon className="h-6 w-6 animate-spin text-pollen" aria-hidden />
      </V4Card>
    );
  }

  return (
    <V4Card className="overflow-hidden p-0">
      <div className="border-b border-(--qs-border) px-4 py-4 md:px-6">
        <V4CardHeader
          as="h2"
          kicker="Admin · god mode"
          title="Platform feature matrix"
          description="Riadenie sekcií a funkcií pre prostredie (globálny kill-switch) a každý typ účtu. Zmeny sa okamžite prejavia v navigácii a route guardoch."
        />
      </div>

      <div className="overflow-x-auto hive-scrollbar v4-platform-matrix">
        <table className="w-full min-w-[960px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-(--qs-border) bg-black/30">
              <th className="v4-platform-matrix-sticky-col sticky left-0 z-20 border-r border-(--qs-border) bg-[#0a0a12] px-4 py-3 font-medium text-(--qs-text-2) lg:min-w-[220px]">
                Sekcia / funkcia
              </th>
              {matrix.profiles.map((profile) => (
                <th
                  key={profile.key}
                  className={cn(
                    "min-w-[140px] px-3 py-3 align-bottom",
                    profileHeaderStyle(profile.tone),
                  )}
                >
                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wide">{profile.label}</span>
                    <span className="text-[10px] font-normal normal-case leading-snug text-(--qs-text-3)">
                      {profile.description}
                    </span>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--xs w-fit gap-1 text-[10px]"
                      disabled={resettingProfile === profile.key}
                      onClick={() => void resetProfile(profile.key)}
                    >
                      {resettingProfile === profile.key ? (
                        <Loader2Icon className="h-3 w-3 animate-spin" aria-hidden />
                      ) : (
                        <RotateCcwIcon className="h-3 w-3" aria-hidden />
                      )}
                      Reset
                    </button>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groupedRows.map((group) => (
              <Fragment key={group.sectionId}>
                <tr key={`section-${group.sectionId}`}>
                  <td
                    className={cn(
                      "v4-platform-matrix-sticky-col sticky left-0 z-20 border-r border-y border-(--qs-border) bg-[#0a0a12] px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] lg:min-w-[220px]",
                      toneStyle(group.sectionTone, "section"),
                    )}
                  >
                    {group.sectionLabel}
                  </td>
                  {matrix.profiles.map((profile) => (
                    <td
                      key={profile.key}
                      className={cn("border-y px-3 py-2", toneStyle(group.sectionTone, "section"))}
                      aria-hidden
                    />
                  ))}
                </tr>
                {group.rows.map((row) => (
                  <tr
                    key={row.feature_key}
                    className="border-b border-(--qs-border)/60 hover:bg-white/[0.02]"
                  >
                    <td className="v4-platform-matrix-sticky-col v4-platform-matrix-label sticky left-0 z-10 border-r border-(--qs-border) bg-[#080810]/95 px-4 py-3 lg:min-w-[220px]">
                      <div className="flex flex-col gap-0.5">
                        <span className="v4-platform-matrix-title font-medium text-(--qs-text)">{row.label}</span>
                        <span className="font-mono text-[10px] text-(--qs-text-3)">{row.feature_key}</span>
                      </div>
                    </td>
                    {matrix.profiles.map((profile) => {
                      const cell = row.cells[profile.key];
                      if (!cell) {
                        return <td key={profile.key} className="px-3 py-3" />;
                      }
                      const cellKey = `${row.feature_key}:${profile.key}`;
                      const isBusy = busyKey === cellKey;
                      const isOverride = cell.source === "override";
                      return (
                        <td key={profile.key} className="px-3 py-3 align-middle text-center">
                          <div className="inline-flex flex-col items-center gap-1.5">
                            <HiveSwitch
                              checked={cell.enabled}
                              disabled={isBusy}
                              aria-label={`${row.label} · ${profile.label}`}
                              onCheckedChange={(next) =>
                                void patchCell(row.feature_key, profile.key, next)
                              }
                            />
                            <button
                              type="button"
                              className={cn(
                                "text-[10px] underline-offset-2 hover:underline",
                                isOverride ? "text-pollen" : "text-(--qs-text-3)",
                              )}
                              disabled={isBusy || !isOverride}
                              onClick={() =>
                                void patchCell(row.feature_key, profile.key, cell.default_enabled, true)
                              }
                            >
                              {isOverride ? "custom" : "default"}
                            </button>
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border-t border-(--qs-border) px-4 py-4 md:px-6">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-cyan">Profile preview</p>
            <p className="text-[11px] text-(--qs-text-3)">
              Simulácia effective feature map — bez prepínania tenanta.
            </p>
          </div>
          <QsSelect
            className="min-w-[min(100%,12rem)] py-2 text-xs capitalize"
            value={previewProfile}
            onValueChange={(next) => setPreviewProfile(next as (typeof PREVIEW_PROFILES)[number])}
            aria-label="Profile preview tier"
            options={PREVIEW_PROFILE_OPTIONS}
          />
        </div>
        {previewLoading && !preview ? (
          <div className="flex min-h-[80px] items-center justify-center">
            <Loader2Icon className="h-5 w-5 animate-spin text-pollen" aria-hidden />
          </div>
        ) : preview ? (
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-(--qs-border) bg-black/30 p-3">
              <p className="font-mono text-[10px] uppercase tracking-wide text-(--qs-text-3)">Enabled ({preview.enabled_count})</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {preview.enabled_features.map((feature) => (
                  <span key={feature} className="rounded bg-[#00FF88]/10 px-2 py-0.5 font-mono text-[10px] text-[#00FF88]">
                    {feature}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-(--qs-border) bg-black/30 p-3">
              <p className="font-mono text-[10px] uppercase tracking-wide text-(--qs-text-3)">Hidden ({preview.disabled_count})</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {preview.disabled_features.map((feature) => (
                  <span key={feature} className="rounded bg-[#FF3366]/10 px-2 py-0.5 font-mono text-[10px] text-[#FF3366]">
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </V4Card>
  );
}
