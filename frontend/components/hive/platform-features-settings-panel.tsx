"use client";

import { Loader2Icon, RotateCcwIcon } from "lucide-react";
import { Fragment, useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import { toast } from "sonner";

import { CollapsibleLazyPanel } from "@/components/hive/collapsible-lazy-panel";
import { usePlatform } from "@/components/hive/platform-context";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";
import { v4SectionToneHeader, v4SectionToneShell } from "@/lib/v4-section-tones";

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

function toneStyle(tone: string, kind: "section" | "header"): string {
  return kind === "section" ? v4SectionToneShell(tone) : v4SectionToneHeader(tone);
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

interface MatrixSectionGroup {
  sectionId: string;
  sectionLabel: string;
  sectionTone: string;
  rows: PlatformFeatureMatrixRow[];
}

interface PlatformMatrixSectionTableProps {
  profiles: PlatformFeatureProfileColumn[];
  group: MatrixSectionGroup;
  busyKey: string | null;
  resettingProfile: string | null;
  onPatch: (featureKey: string, profileKey: string, enabled: boolean, revertToDefault?: boolean) => Promise<void>;
  onReset: (profileKey: string) => Promise<void>;
}

function PlatformMatrixSectionTable({
  profiles,
  group,
  busyKey,
  resettingProfile,
  onPatch,
  onReset,
}: PlatformMatrixSectionTableProps): JSX.Element {
  const gridStyle = {
    "--v4-matrix-cols": String(profiles.length),
  } as CSSProperties;

  return (
    <div className="hive-scrollbar v4-platform-matrix">
      <div className="v4-platform-matrix-scroll">
        <div className="v4-platform-matrix-grid text-sm" style={gridStyle} role="table">
          <div className="v4-platform-matrix-corner v4-platform-matrix-sticky-col" role="columnheader">
            Section / feature
          </div>
          {profiles.map((profile) => (
            <div
              key={profile.key}
              className={cn("v4-platform-matrix-col-head", profileHeaderStyle(profile.tone))}
              role="columnheader"
            >
              <span className="v4-platform-matrix-col-title">{profile.label}</span>
              <span className="v4-platform-matrix-col-desc">{profile.description}</span>
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--xs v4-platform-matrix-reset gap-1 text-[10px]"
                disabled={resettingProfile === profile.key}
                onClick={() => void onReset(profile.key)}
              >
                {resettingProfile === profile.key ? (
                  <Loader2Icon className="h-3 w-3 animate-spin" aria-hidden />
                ) : (
                  <RotateCcwIcon className="h-3 w-3" aria-hidden />
                )}
                Reset
              </button>
            </div>
          ))}

          {group.rows.map((row) => (
            <Fragment key={row.feature_key}>
              <div className="v4-platform-matrix-row-label v4-platform-matrix-sticky-col" role="rowheader">
                <span className="v4-platform-matrix-title font-medium text-(--qs-text)">{row.label}</span>
                <span className="font-mono text-[10px] text-(--qs-text-3)">{row.feature_key}</span>
              </div>
              {profiles.map((profile) => {
                const cell = row.cells[profile.key];
                if (!cell) {
                  return <div key={profile.key} className="v4-platform-matrix-cell v4-platform-matrix-cell--empty" role="cell" />;
                }
                const cellKey = `${row.feature_key}:${profile.key}`;
                const isBusy = busyKey === cellKey;
                const isOverride = cell.source === "override";
                return (
                  <div key={profile.key} className="v4-platform-matrix-cell" role="cell">
                    <HiveSwitch
                      checked={cell.enabled}
                      disabled={isBusy}
                      aria-label={`${row.label} · ${profile.label}`}
                      onCheckedChange={(next) => void onPatch(row.feature_key, profile.key, next)}
                    />
                    <button
                      type="button"
                      className={cn(
                        "v4-platform-matrix-source text-[10px] underline-offset-2 hover:underline",
                        isOverride ? "text-pollen" : "text-(--qs-text-3)",
                      )}
                      disabled={isBusy || !isOverride}
                      onClick={() => void onPatch(row.feature_key, profile.key, cell.default_enabled, true)}
                    >
                      {isOverride ? "custom" : "default"}
                    </button>
                  </div>
                );
              })}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

interface PlatformFeaturePreviewPanelProps {
  previewProfile: (typeof PREVIEW_PROFILES)[number];
  onPreviewProfileChange: (profile: (typeof PREVIEW_PROFILES)[number]) => void;
  preview: PlatformFeaturePreviewPayload | null;
  previewLoading: boolean;
}

function PlatformFeaturePreviewPanel({
  previewProfile,
  onPreviewProfileChange,
  preview,
  previewLoading,
}: PlatformFeaturePreviewPanelProps): JSX.Element {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan">Profile preview</p>
          <p className="text-[11px] text-(--qs-text-3)">
            Effective feature map simulation — without switching tenant.
          </p>
        </div>
        <QsSelect
          className="min-w-[min(100%,12rem)] py-2 text-xs capitalize"
          value={previewProfile}
          onValueChange={(next) => onPreviewProfileChange(next as (typeof PREVIEW_PROFILES)[number])}
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
          <div className="v4-platform-matrix-preview-bubble v4-platform-matrix-preview-bubble--enabled">
            <p className="font-mono text-[10px] uppercase tracking-wide text-(--qs-text-3)">
              Enabled ({preview.enabled_count})
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {preview.enabled_features.map((feature) => (
                <span key={feature} className="v4-platform-matrix-chip v4-platform-matrix-chip--enabled">
                  {feature}
                </span>
              ))}
            </div>
          </div>
          <div className="v4-platform-matrix-preview-bubble v4-platform-matrix-preview-bubble--hidden">
            <p className="font-mono text-[10px] uppercase tracking-wide text-(--qs-text-3)">
              Hidden ({preview.disabled_count})
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {preview.disabled_features.map((feature) => (
                <span key={feature} className="v4-platform-matrix-chip v4-platform-matrix-chip--hidden">
                  {feature}
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
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
  const [previewOpen, setPreviewOpen] = useState(false);

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
    if (previewOpen) {
      void loadPreview();
    }
  }, [previewOpen, previewProfile, loadPreview]);

  const groupedRows = useMemo(() => {
    if (!matrix) {
      return [];
    }
    const groups: MatrixSectionGroup[] = [];
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
        toast.success(revertToDefault ? "Restored default" : "Saved");
        if (previewOpen) {
          await loadPreview();
        }
      } catch (error) {
        const msg = error instanceof HiveApiError ? error.message : "Save failed.";
        toast.error(msg);
        await load();
      } finally {
        setBusyKey(null);
      }
    },
    [load, loadPreview, previewOpen, refresh],
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
        if (previewOpen) {
          await loadPreview();
        }
        toast.success("Column reset to catalog defaults");
      } catch (error) {
        const msg = error instanceof HiveApiError ? error.message : "Reset zlyhal.";
        toast.error(msg);
      } finally {
        setResettingProfile(null);
      }
    },
    [loadPreview, previewOpen, refresh],
  );

  if (!allowed) {
    return (
      <V4Card>
        <V4CardHeader
          title="Platform features"
          description="Available only to the admin account in the internal (operator) tenant."
        />
        <p className="px-4 pb-4 text-sm text-(--qs-text-3)">
          Sign in as admin and switch to the operator workspace.
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
          description="Toggle sections and features per environment (global kill-switch) and account tier. Changes apply immediately in navigation and route guards."
        />
      </div>

      <div className="space-y-3 px-4 py-4 md:px-6">
        {groupedRows.map((group) => (
          <CollapsibleLazyPanel
            key={group.sectionId}
            id={`platform-section-${group.sectionId}`}
            hashKey={`platform-${group.sectionId}`}
            title={group.sectionLabel}
            hint={`${group.rows.length} features · profile toggles`}
            meta={`${group.rows.length} features`}
            className={cn("border", toneStyle(group.sectionTone, "section"))}
            panelClassName="pt-2"
            lazyContent={() => (
              <PlatformMatrixSectionTable
                profiles={matrix.profiles}
                group={group}
                busyKey={busyKey}
                resettingProfile={resettingProfile}
                onPatch={patchCell}
                onReset={resetProfile}
              />
            )}
          />
        ))}

        <CollapsibleLazyPanel
          id="platform-profile-preview"
          hashKey="platform-preview"
          title="Profile preview"
          hint="Effective feature map simulation"
          meta={preview ? `${preview.enabled_count} on` : undefined}
          onOpenChange={setPreviewOpen}
          lazyContent={() => (
            <PlatformFeaturePreviewPanel
              previewProfile={previewProfile}
              onPreviewProfileChange={setPreviewProfile}
              preview={preview}
              previewLoading={previewLoading}
            />
          )}
        />
      </div>
    </V4Card>
  );
}
