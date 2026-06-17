"use client";

import Link from "next/link";
import { BookOpen, CalendarClock, Loader2, Settings2, Tag } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";

type ReviewCronPreset = "off" | "daily_0600" | "daily_2000" | "weekly_monday" | "custom";
type StudioPreset = "trading" | "business_brain";

interface JournalStudioSettings {
  enabled: boolean;
  field_toggles: Record<string, boolean>;
  review_cron_enabled: boolean;
  review_cron_preset: ReviewCronPreset;
  review_cron: string;
  obsidian_subfolder: string;
  mistake_tags: string[];
  studio_preset: StudioPreset;
  field_labels: Record<string, string>;
  pattern_tags_label: string;
  wiki_capture_href: string;
  brief_dispatch_href: string;
  source: "deployment" | "tenant";
}

interface JournalRoutineKpi {
  enabled: boolean;
  routine_status: string;
  routine_id: string | null;
  routine_name: string;
  next_run_at: string | null;
  review_cron: string;
  review_cron_preset: ReviewCronPreset;
  obsidian_subfolder: string;
  enabled_field_count: number;
  mistake_tag_count: number;
  operator_hint: string;
}

const FIELD_LABELS: Record<string, string> = {
  thesis: "Thesis",
  setup: "Setup",
  entry_price: "Entry price",
  exit_price: "Exit price",
  position_size: "Position size",
  outcome: "Outcome",
  pnl: "P&L",
  emotion: "Emotion",
  screenshot: "Screenshot",
  lesson: "Lesson learned",
  tags: "Tags",
  mistake_tag: "Mistake tag",
};

const PRESET_OPTIONS: { value: StudioPreset; label: string }[] = [
  { value: "trading", label: "Trading journal" },
  { value: "business_brain", label: "Business brain (Moneta / marketing)" },
];

const CRON_PRESET_OPTIONS: { value: ReviewCronPreset; label: string }[] = [
  { value: "off", label: "Off" },
  { value: "daily_0600", label: "Daily 06:00 UTC" },
  { value: "daily_2000", label: "Daily 20:00 UTC" },
  { value: "weekly_monday", label: "Weekly Monday 07:00 UTC" },
  { value: "custom", label: "Custom cron" },
];

function routineTone(status: string): "ok" | "warn" | "info" | "purple" {
  if (status === "ready" || status === "scheduled") return "ok";
  if (status === "running") return "info";
  if (status === "missing") return "warn";
  return "purple";
}

export function JournalStudioSettingsPanel(): JSX.Element | null {
  const [settings, setSettings] = useState<JournalStudioSettings | null>(null);
  const [draft, setDraft] = useState<JournalStudioSettings | null>(null);
  const [kpi, setKpi] = useState<JournalRoutineKpi | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [tagInput, setTagInput] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [settingsData, kpiData] = await Promise.all([
        hiveGet<JournalStudioSettings>("journal-studio/settings"),
        hiveGet<JournalRoutineKpi>("journal-studio/routine"),
      ]);
      setSettings(settingsData);
      setDraft(settingsData);
      setKpi(kpiData);
    } catch {
      setSettings(null);
      setDraft(null);
      setKpi(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = useCallback(async () => {
    if (!draft) return;
    setSaving(true);
    try {
      const data = await hivePatchJson<JournalStudioSettings>("journal-studio/settings", {
        enabled: draft.enabled,
        field_toggles: draft.field_toggles,
        review_cron_enabled: draft.review_cron_enabled,
        review_cron_preset: draft.review_cron_preset,
        review_cron: draft.review_cron,
        obsidian_subfolder: draft.obsidian_subfolder,
        mistake_tags: draft.mistake_tags,
        studio_preset: draft.studio_preset,
      });
      setSettings(data);
      setDraft(data);
      const kpiData = await hiveGet<JournalRoutineKpi>("journal-studio/routine");
      setKpi(kpiData);
      toast.success("Journal studio settings saved.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [draft]);

  const bootstrap = useCallback(async () => {
    setBootstrapping(true);
    try {
      await hivePostJson("journal-studio/routine/bootstrap", {});
      await load();
      toast.success("Review routine registered.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Bootstrap failed");
    } finally {
      setBootstrapping(false);
    }
  }, [load]);

  const addTag = useCallback(() => {
    if (!draft || !tagInput.trim()) return;
    const tag = tagInput.trim().toLowerCase().replace(/\s+/g, "_");
    if (draft.mistake_tags.includes(tag)) {
      setTagInput("");
      return;
    }
    setDraft({ ...draft, mistake_tags: [...draft.mistake_tags, tag] });
    setTagInput("");
  }, [draft, tagInput]);

  const removeTag = useCallback(
    (tag: string) => {
      if (!draft) return;
      setDraft({ ...draft, mistake_tags: draft.mistake_tags.filter((row) => row !== tag) });
    },
    [draft],
  );

  if (loading) {
    return (
      <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60" data-testid="journal-studio-settings-panel">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading journal studio settings…
      </V4Card>
    );
  }

  if (!draft) {
    return null;
  }

  return (
    <div className="space-y-4" data-testid="journal-studio-settings-panel">
      <V4Card id="journal-studio-settings" className="border-amber-500/25">
        <V4CardHeader
          kicker="Track O · TJ4"
          title="Studio settings"
          description="Configure journal fields, overnight review cron, Obsidian vault subfolder, and mistake tags."
          actions={
            <div className="flex items-center gap-2">
              <V4Badge tone={draft.enabled ? "ok" : "warn"}>{draft.enabled ? "Active" : "Off"}</V4Badge>
              <HiveRefreshButton busy={loading} onClick={() => void load()} />
            </div>
          }
        />
        <div className="space-y-4 px-4 pb-4">
          <label className="block text-sm">
            <span className="text-white/60">Studio preset (TJ7)</span>
            <select
              className="qs-input mt-1 w-full"
              value={draft.studio_preset}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  studio_preset: e.target.value as StudioPreset,
                })
              }
            >
              {PRESET_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          {draft.studio_preset === "business_brain" ? (
            <div className="flex flex-wrap gap-2 text-xs">
              <Link href={draft.wiki_capture_href} className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1">
                <BookOpen className="size-3.5" aria-hidden />
                Wiki capture
              </Link>
              <Link href={draft.brief_dispatch_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                NP4 brief dispatch
              </Link>
            </div>
          ) : null}

          <label className="flex items-center gap-2 text-sm text-white/80">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
            />
            Enable Learning Loop Studio
          </label>

          <div>
            <p className="mb-2 text-sm font-medium text-white/80">Journal fields</p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(draft.field_labels ?? FIELD_LABELS).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 text-sm text-white/70">
                  <input
                    type="checkbox"
                    checked={Boolean(draft.field_toggles[key])}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        field_toggles: { ...draft.field_toggles, [key]: e.target.checked },
                      })
                    }
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-white/60">Review cron preset</span>
              <select
                className="qs-input mt-1 w-full font-mono"
                value={draft.review_cron_preset}
                onChange={(e) => {
                  const preset = e.target.value as ReviewCronPreset;
                  setDraft({
                    ...draft,
                    review_cron_preset: preset,
                    review_cron_enabled: preset !== "off",
                  });
                }}
              >
                {CRON_PRESET_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-white/60">Obsidian subfolder</span>
              <input
                className="qs-input mt-1 w-full font-mono"
                value={draft.obsidian_subfolder}
                onChange={(e) => setDraft({ ...draft, obsidian_subfolder: e.target.value })}
                placeholder="Trading/Journal"
              />
            </label>
          </div>

          {draft.review_cron_preset === "custom" ? (
            <label className="block text-sm">
              <span className="text-white/60">Custom cron (minute hour dom month dow)</span>
              <input
                className="qs-input mt-1 w-full font-mono"
                value={draft.review_cron}
                onChange={(e) => setDraft({ ...draft, review_cron: e.target.value })}
              />
            </label>
          ) : null}

          <div>
            <p className="mb-2 flex items-center gap-1.5 text-sm font-medium text-white/80">
              <Tag className="size-4" aria-hidden />
              {draft.pattern_tags_label || "Mistake tags"}
            </p>
            <div className="flex flex-wrap gap-2">
              {draft.mistake_tags.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--xs font-mono"
                  onClick={() => removeTag(tag)}
                  title="Remove tag"
                >
                  {tag} ×
                </button>
              ))}
            </div>
            <div className="mt-2 flex gap-2">
              <input
                className="qs-input flex-1 font-mono"
                value={tagInput}
                placeholder="Add tag…"
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addTag();
                  }
                }}
              />
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={addTag}>
                Add
              </button>
            </div>
          </div>

          <p className="text-xs text-white/50">Source: {settings?.source ?? draft.source}. Vault writes require operator approve.</p>

          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm inline-flex gap-1.5"
            disabled={saving}
            onClick={() => void save()}
          >
            {saving ? <Loader2 className="size-4 animate-spin" /> : <Settings2 className="size-4" />}
            Save settings
          </button>
        </div>
      </V4Card>

      <div data-testid="journal-studio-routine-panel">
        <V4Card className="border-cyan-500/20">
          <V4CardHeader
            kicker="Overnight review"
            title={kpi?.routine_name ?? "Trading journal review"}
            description={kpi?.operator_hint ?? "Bootstrap cron to schedule draft reviews."}
            actions={
              kpi ? (
                <V4Badge tone={routineTone(kpi.routine_status)}>{kpi.routine_status}</V4Badge>
              ) : null
            }
          />
          <div className="space-y-3 px-4 pb-4 text-sm text-white/70">
            <div className="flex flex-wrap gap-3 font-mono text-xs">
              <span className="inline-flex items-center gap-1">
                <CalendarClock className="size-3.5 text-cyan" aria-hidden />
                {kpi?.review_cron ?? draft.review_cron}
              </span>
              <span className="inline-flex items-center gap-1">
                <BookOpen className="size-3.5 text-amber" aria-hidden />
                {kpi?.obsidian_subfolder ?? draft.obsidian_subfolder}
              </span>
              <span>{kpi?.enabled_field_count ?? 0} fields · {kpi?.mistake_tag_count ?? draft.mistake_tags.length} tags</span>
            </div>
            {kpi?.routine_status === "missing" ? (
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm inline-flex gap-1.5"
                disabled={bootstrapping}
                onClick={() => void bootstrap()}
              >
                {bootstrapping ? <Loader2 className="size-4 animate-spin" /> : <CalendarClock className="size-4" />}
                Bootstrap review routine
              </button>
            ) : null}
          </div>
        </V4Card>
      </div>
    </div>
  );
}
