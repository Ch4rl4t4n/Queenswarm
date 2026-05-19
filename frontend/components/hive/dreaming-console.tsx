"use client";

import { Loader2Icon, Moon, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { InfoHint } from "@/components/hive/info-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import { cn } from "@/lib/utils";

interface DreamingSettingsResponse {
  enabled: boolean;
  frequency_hours: number;
  routine_id: string | null;
}

interface DreamCycleRow {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  items_processed: number;
  items_deduplicated: number;
  items_consolidated: number;
}

interface RunNowResponse {
  status: string;
  celery_task_id: string;
}

function cycleStatusTone(status: string): "ok" | "warn" | "err" | "info" {
  const s = status.toLowerCase();
  if (s.includes("complete") || s.includes("success")) {
    return "ok";
  }
  if (s.includes("fail") || s.includes("error")) {
    return "err";
  }
  if (s.includes("run") || s.includes("queue") || s.includes("pending")) {
    return "info";
  }
  return "warn";
}

/** Tenant-scoped dreaming controls — Hive Control V4. */
export function DreamingConsole(): JSX.Element {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [settings, setSettings] = useState<DreamingSettingsResponse | null>(null);
  const [cycles, setCycles] = useState<DreamCycleRow[]>([]);
  const [frequencyHours, setFrequencyHours] = useState(24);
  const [lastRunTaskId, setLastRunTaskId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, rows] = await Promise.all([
        hiveGet<DreamingSettingsResponse>("dreaming/settings"),
        hiveGet<DreamCycleRow[]>("dreaming/cycles?limit=8"),
      ]);
      setSettings(s);
      setFrequencyHours(Math.max(1, Math.min(168, Number(s.frequency_hours || 24))));
      setCycles(rows);
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Dreaming data unavailable.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function persist(nextEnabled: boolean): Promise<void> {
    setSaving(true);
    setError(null);
    try {
      const next = await hivePutJson<DreamingSettingsResponse>("dreaming/settings", {
        enabled: nextEnabled,
        frequency_hours: Math.max(1, Math.min(168, frequencyHours)),
      });
      setSettings(next);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Could not update dreaming settings.";
      setError(detail);
    } finally {
      setSaving(false);
    }
  }

  async function runNow(): Promise<void> {
    setRunning(true);
    setError(null);
    try {
      const out = await hivePostJson<RunNowResponse>("dreaming/run-now", {});
      setLastRunTaskId(out.celery_task_id);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Manual dreaming trigger failed.";
      setError(detail);
    } finally {
      setRunning(false);
    }
  }

  const enabled = settings?.enabled ?? false;

  return (
    <div className="flex flex-col gap-8">
      <div className="v4-learning-lane">
        <Moon className="h-4 w-4 shrink-0 text-(--qs-purple-bright)" aria-hidden />
        <div>
          <p className="v4-label-kicker">Nightly memory lane</p>
          <p className="text-xs text-(--qs-text-3)">
            Celery beat consolidates supervisor history into HiveMind · tenant-scoped dream reports.
          </p>
        </div>
        {enabled ? <V4Badge tone="ok">Scheduled</V4Badge> : <V4Badge tone="warn">Paused</V4Badge>}
      </div>

      <V4Card>
        <V4CardHeader
          title="Dreaming · nightly memory cycles"
          description="Tenant-scoped consolidation of supervisor history into HiveMind knowledge and Dream Reports."
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                disabled={running || loading}
                onClick={() => void runNow()}
              >
                {running ? <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Play className="h-3.5 w-3.5" aria-hidden />}
                {running ? "Queueing…" : "Run now"}
              </button>
              <button
                type="button"
                className={cn("qs-btn qs-btn--sm", enabled ? "qs-btn--ghost" : "qs-btn--primary")}
                disabled={saving || loading}
                onClick={() => void persist(!enabled)}
              >
                {saving ? "Saving…" : enabled ? "Disable dreaming" : "Enable dreaming"}
              </button>
            </div>
          }
        />

        {loading ? (
          <p className="mb-4 flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
            Loading dreaming controls…
          </p>
        ) : null}
        {error ? <p className="mb-4 text-sm text-(--qs-red)">{error}</p> : null}

        <section className="v4-learning-panel">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-(--qs-text)">Memory + Dreaming</h3>
              <p className="mt-1 text-xs text-(--qs-text-3)">
                Automatický proces učenia — supervisor sessions → vzory, chyby, Dream Report v HiveMind.
              </p>
            </div>
            <InfoHint
              title="Čo je Memory + Dreaming?"
              description="Automatický proces učenia. Systém prečíta minulé supervisor sessions, nájde užitočné vzory a chyby, a uloží zhrnutie do HiveMind ako Dream Report."
              options={[
                "Učí sa bez manuálneho zásahu",
                "Všetko je oddelené podľa tenantu",
                "Nové poznatky nájdeš v Knowledge sekcii",
              ]}
            />
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
            <label className="block">
              <span className="v4-field-label inline-flex items-center gap-2">
                Frequency (hours)
                <InfoHint
                  title="Frekvencia Dreaming behu"
                  description="Určuje, ako často sa spustí automatické učenie. Menšie číslo znamená častejšie učenie, ale aj vyššiu spotrebu výpočtu."
                  options={[
                    "24 = raz denne (odporúčané)",
                    "1-8 = častejšie učenie pri aktívnej prevádzke",
                    "168 = raz týždenne pri nízkej aktivite",
                  ]}
                />
              </span>
              <input
                type="number"
                min={1}
                max={168}
                value={frequencyHours}
                disabled={saving || loading}
                onChange={(event) => setFrequencyHours(Number(event.target.value || 24))}
                className="qs-input mt-1.5 min-h-11 w-full rounded-(--qs-radius-sm) font-mono"
              />
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                disabled={running || loading}
                onClick={() => void runNow()}
              >
                {running ? "Queueing…" : "Run dreaming now"}
              </button>
              <InfoHint
                title="Run Dreaming now"
                description="Ručné okamžité spustenie. Použi ho po väčších zmenách alebo po sérii incidentov, aby si hneď získal nový Dream Report."
                options={[
                  "Spustí sa jednorazový job",
                  "Nečaká na plánovaný čas",
                  "Výsledok sa objaví v Latest Dream Reports",
                ]}
              />
            </div>
          </div>

          {lastRunTaskId ? (
            <p className="mt-3 font-mono text-[11px] text-(--qs-cyan)">Manual run queued: {lastRunTaskId}</p>
          ) : null}
        </section>

        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <p className="v4-label-kicker">Latest dream reports</p>
            <InfoHint
              title="Latest Dream Reports"
              description="Prehľad posledných behov Dreaming. Každý riadok ukazuje, koľko dát systém spracoval a koľko duplicít zlúčil."
              options={[
                "status: stav behu (completed/failed)",
                "consolidated: počet nových konsolidovaných poznatkov",
                "dedup: počet odstránených duplicitných signálov",
              ]}
            />
          </div>

          {cycles.length === 0 ? (
            <p className="v4-dream-empty">No dream reports yet.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {cycles.map((row) => (
                <li key={row.id} className="v4-dream-cycle-card">
                  <div className="flex items-start gap-3">
                    <Moon className="mt-0.5 h-5 w-5 shrink-0 text-(--qs-purple-bright)" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="v4-label-kicker">{new Date(row.started_at).toLocaleString("sk-SK")}</span>
                        <V4Badge tone={cycleStatusTone(row.status)}>{row.status}</V4Badge>
                      </div>
                      <p className="mt-2 text-sm text-(--qs-text-2)">
                        processed={row.items_processed} · consolidated=
                        <span className="text-(--qs-amber)">{row.items_consolidated}</span> · dedup=
                        <span className="text-(--qs-cyan)">{row.items_deduplicated}</span>
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </V4Card>
    </div>
  );
}
