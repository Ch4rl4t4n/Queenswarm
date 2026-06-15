"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { InfoHint } from "@/components/hive/info-hint";
import { TokenBudgetMeterPanel } from "@/components/hive/token-budget-meter-panel";
import { Tier0InjectionStripPanel } from "@/components/hive/tier0-injection-strip-panel";
import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";

type BrainTab = "soul" | "memory" | "user" | "brand";

const BRAIN_TABS: { id: BrainTab; label: string; hint: string }[] = [
  { id: "soul", label: "SOUL", hint: "Identity, tone, skills hierarchy" },
  { id: "memory", label: "MEMORY", hint: "Mission + ideal state (project facts)" },
  { id: "user", label: "USER", hint: "Behavioral instructions (operator prefs)" },
  { id: "brand", label: "BRAND", hint: "Voice, forbidden claims, examples — marketing harness only (NP3)" },
];

const SOUL_KINDS = ["soul", "skills_hierarchy"] as const;
const MEMORY_KINDS = ["mission", "ideal_state"] as const;
const USER_KINDS = ["instructions"] as const;
const BRAND_KINDS = ["brand"] as const;

const BRAIN_PACK_HINT = {
  title: { en: "Operator Brain Pack", sk: "Operator Brain Pack" },
  description: {
    en: "Three-tier Queen context (SOUL, MEMORY, USER). Injected as === BEHAVIORAL INSTRUCTIONS === on every Queen bootstrap.",
    sk: "Trojvrstvový kontext pre Queen (SOUL, MEMORY, USER). Pri každom bootstrap sa vloží ako === BEHAVIORAL INSTRUCTIONS ===.",
  },
  options: {
    en: [
      "Load starter pack — Queenswarm solo-operator defaults (empty slots only).",
      "Edit SOUL (tone + skills), MEMORY (mission + ideal state), USER (your preferences).",
      "Export .md — copy Hermes-style bundle for backup.",
      "Social OAuth: see docs/OPERATOR_SOCIAL_OAUTH_SETUP.md in repo.",
    ],
    sk: [
      "Načítať starter pack — predvolené texty pre solo operátora (len prázdne polia).",
      "Uprav SOUL (tón + skills), MEMORY (misia + ideál), USER (tvoje preferencie po slovensky).",
      "Export .md — záloha Hermes-style balíka.",
      "Social OAuth: docs/OPERATOR_SOCIAL_OAUTH_SETUP.md v repozitári.",
    ],
  },
};

/** Hermes-style Operator Brain Pack — maps to existing curated memory kinds. */
export function OperatorBrainPackPanel() {
  const [bundle, setBundle] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<BrainTab>("soul");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [maxChars, setMaxChars] = useState(16_000);
  const [refreshMeter, setRefreshMeter] = useState(0);

  const reload = useCallback(async () => {
    try {
      const [data, limits] = await Promise.all([
        hiveGet<Record<string, string>>("memory/curated"),
        hiveGet<{ max_chars_per_file: number }>("memory/curated/limits"),
      ]);
      setBundle(data);
      setDrafts(data);
      setMaxChars(limits.max_chars_per_file);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Brain pack unavailable");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const activeKinds =
    tab === "soul"
      ? SOUL_KINDS
      : tab === "memory"
        ? MEMORY_KINDS
        : tab === "brand"
          ? BRAND_KINDS
          : USER_KINDS;

  const activeCharCount = activeKinds.reduce(
    (sum, kind) => sum + (drafts[kind] ?? bundle[kind] ?? "").length,
    0,
  );

  async function saveTab() {
    setBusy(true);
    try {
      for (const kind of activeKinds) {
        await hivePutJson(`memory/curated/${encodeURIComponent(kind)}`, {
          content_md: drafts[kind] ?? "",
        });
      }
      toast.success("Brain pack saved");
      setRefreshMeter((value) => value + 1);
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function exportPack() {
    try {
      const body = await hiveGet<{ markdown: string }>("memory/curated/export/brain-pack");
      await navigator.clipboard.writeText(body.markdown);
      toast.success("Brain pack copied to clipboard");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Export failed");
    }
  }

  async function loadStarterPack() {
    setBusy(true);
    try {
      const result = await hivePostJson<{ seeded_kinds: string[]; skipped_kinds: string[] }>(
        "memory/curated/seed-brain-pack",
        { overwrite: false },
      );
      if (result.seeded_kinds.length) {
        toast.success(`Starter loaded: ${result.seeded_kinds.join(", ")}`);
      } else {
        toast.info("All slots already filled — edit manually or use overwrite via API");
      }
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Starter pack failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <V4Card id={tab === "brand" ? "brain-pack-brand" : "brain-pack"}>
      <V4CardHeader
        kicker="Operator Brain Pack"
        title="SOUL · MEMORY · USER · BRAND"
        description="Hermes-style identity + NP3 brand context. Queen reads SOUL/MEMORY/USER on every bootstrap; BRAND injects in marketing harness sessions only."
        hint={
          <InfoHint
            title={BRAIN_PACK_HINT.title}
            description={BRAIN_PACK_HINT.description}
            options={BRAIN_PACK_HINT.options}
            className="hive-inline-hint"
          />
        }
      />
      {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
      <TokenBudgetMeterPanel refreshKey={refreshMeter} className="mb-3" />
      <Tier0InjectionStripPanel refreshKey={refreshMeter} className="mb-3" />
      <div className="mb-3 flex flex-wrap gap-2">
        {BRAIN_TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={tab === item.id ? "qs-btn qs-btn--primary qs-btn--sm" : "qs-btn qs-btn--ghost qs-btn--sm"}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void loadStarterPack()} disabled={busy}>
          Load starter pack
        </button>
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm ml-auto" onClick={() => void exportPack()}>
          Export .md
        </button>
      </div>
      <p className="mb-3 text-xs text-(--qs-muted)">
        {BRAIN_TABS.find((t) => t.id === tab)?.hint}
        {tab === "brand" ? (
          <span className="ml-2 font-mono text-cyan">
            {activeCharCount}/{maxChars} chars · injection cap ~1300 in marketing sessions
          </span>
        ) : null}
      </p>
      <div className="space-y-4">
        {activeKinds.map((kind) => (
          <div key={kind}>
            <label className="mb-1 block font-mono text-xs uppercase text-cyan">{kind}</label>
            <textarea
              value={drafts[kind] ?? bundle[kind] ?? ""}
              onChange={(e) => setDrafts((prev) => ({ ...prev, [kind]: e.target.value }))}
              rows={tab === "user" ? 10 : tab === "brand" ? 14 : 8}
              className="qs-input min-h-[160px] w-full font-mono text-xs leading-relaxed"
              placeholder={`Markdown for ${kind}…`}
            />
          </div>
        ))}
      </div>
      <div className="mt-3 flex justify-end">
        <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={busy} onClick={() => void saveTab()}>
          {busy ? "Saving…" : "Save tab"}
        </button>
      </div>
    </V4Card>
  );
}
