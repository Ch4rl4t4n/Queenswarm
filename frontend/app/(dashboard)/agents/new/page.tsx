"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

const AGENT_TEMPLATES = [
  {
    id: "crypto_scout",
    label: "Crypto Scout",
    emoji: "📊",
    color: "#00E5FF",
    system_prompt:
      "You are a crypto market intelligence agent. Monitor token prices, sentiment, news, and on-chain signals. Provide data-backed analysis with explicit confidence scores.",
    user_prompt:
      "Analyze current market conditions. Provide: 1) Price & 24h change 2) Sentiment (bull/bear/neutral with %) 3) Top 3 signals 4) Recommendation with reasoning.",
    tools: ["web_search", "coingecko"],
    output_format: "markdown",
  },
  {
    id: "blog_writer",
    label: "Blog Writer",
    emoji: "✍️",
    color: "#00FF88",
    system_prompt:
      "You are an SEO content writer. Produce engaging, optimized posts with meta description, headings, and CTA.",
    user_prompt:
      "Write a ~500-word SEO blog on the topic. Include title, meta description, 3 H2 sections, conclusion, and CTA.",
    tools: ["web_search", "wikipedia"],
    output_format: "markdown",
  },
  {
    id: "instagram_manager",
    label: "Instagram Manager",
    emoji: "📸",
    color: "#FF00AA",
    system_prompt: "You are a social strategist for Instagram. Produce scroll-stopping captions and hashtag sets.",
    user_prompt:
      "Create 3 post variations: caption (≤150 chars), 10 hashtags, emojis, CTA.",
    tools: ["web_search"],
    output_format: "text",
  },
  {
    id: "news_digest",
    label: "News Digest",
    emoji: "📰",
    color: "#FFB800",
    system_prompt: "You curate news into concise, cited briefings.",
    user_prompt:
      "Summarize the top five signals from configured feeds — headline, 2-sentence summary, why it matters, impact score 1–10.",
    tools: ["rss", "web_search"],
    output_format: "markdown",
  },
  {
    id: "custom",
    label: "Custom Agent",
    emoji: "🐝",
    color: "#FFB800",
    system_prompt: "",
    user_prompt: "",
    tools: [],
    output_format: "text",
  },
] as const;

const ALL_TOOLS = [
  { id: "web_search", label: "Web Search", desc: "Search index (DuckDuckGo-style)" },
  { id: "youtube", label: "YouTube", desc: "Requires API credentials when enabled" },
  { id: "coingecko", label: "CoinGecko", desc: "Pricing feeds" },
  { id: "rss", label: "RSS", desc: "Feeds" },
  { id: "scrape_url", label: "Scrape URL", desc: "Fetched pages" },
  { id: "wikipedia", label: "Wikipedia", desc: "Article summaries" },
] as const;

const OUTPUT_FORMATS = [
  { id: "text", label: "Plain text" },
  { id: "markdown", label: "Markdown" },
  { id: "json", label: "JSON" },
  { id: "excel", label: "Excel (.xlsx)" },
  { id: "csv", label: "CSV" },
] as const;

const SCHEDULE_PRESETS = [
  { label: "On demand", value: "" },
  { label: "Every hour", value: "every 1 hours" },
  { label: "Every 4 hours", value: "every 4 hours" },
  { label: "Every 12 hours", value: "every 12 hours" },
  { label: "Daily 08:00", value: "daily 08:00" },
  { label: "Daily 20:00", value: "daily 20:00" },
] as const;

interface SwarmLite {
  id: string;
  name: string;
  purpose?: string;
  member_count?: number;
  is_active?: boolean;
  local_memory?: Record<string, unknown> | null;
}

interface DynamicCreateResponse {
  agent_id: string;
  agent_name: string;
  config_id: string;
}

function swarmDisplayRole(sw: Pick<SwarmLite, "local_memory" | "purpose">): string {
  const lm = sw.local_memory ?? {};
  const hi = (lm.hive_ui as Record<string, unknown> | undefined) ?? {};
  const label = (hi.swarm_role_label as string) || (lm.swarm_role_label as string);
  if (label?.trim()) return label;
  return String(sw.purpose ?? "colony").replace(/_/g, " ");
}

function swarmAccentHex(sw: Pick<SwarmLite, "local_memory" | "purpose">): string {
  const lm = sw.local_memory ?? {};
  const hi = (lm.hive_ui as Record<string, unknown> | undefined) ?? {};
  const hex = (hi.swarm_color_hex as string) || (lm.swarm_color_hex as string);
  if (hex?.startsWith("#")) return hex;
  const p = String(sw.purpose ?? "").toLowerCase();
  if (p.includes("scout")) return "#00E5FF";
  if (p.includes("eval")) return "#FFB800";
  if (p.includes("sim")) return "#FF00AA";
  return "#00FF88";
}

function NewAgentWizardInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [step, setStep] = useState<"template" | "configure">("template");
  const [selectedTemplate, setSelectedTemplate] = useState<(typeof AGENT_TEMPLATES)[number] | null>(null);
  const [swarms, setSwarms] = useState<SwarmLite[]>([]);
  const [saving, setSaving] = useState(false);

  const swarmParam = searchParams.get("swarm_id") ?? "";

  const [config, setConfig] = useState({
    name: "",
    swarm_id: swarmParam,
    system_prompt: "",
    user_prompt: "",
    tools: [] as string[],
    output_format: "text",
    output_destination: "dashboard",
    schedule_value: "",
    output_config: {} as Record<string, string>,
  });

  useEffect(() => {
    if (swarmParam) {
      setConfig((c) => ({ ...c, swarm_id: swarmParam }));
    }
  }, [swarmParam]);

  useEffect(() => {
    void hiveGet<unknown>("swarms?limit=200")
      .then((d) => {
        const rows = Array.isArray(d)
          ? d
          : Array.isArray((d as { items?: unknown }).items)
            ? (d as { items: unknown[] }).items
            : Array.isArray((d as { swarms?: unknown }).swarms)
              ? (d as { swarms: unknown[] }).swarms
              : [];
        setSwarms(
          rows
            .filter((r): r is SwarmLite => typeof r === "object" && r !== null && "id" in r && "name" in r)
            .map((r) => ({
              ...r,
              local_memory:
                r.local_memory && typeof r.local_memory === "object"
                  ? (r.local_memory as Record<string, unknown>)
                  : undefined,
            })),
        );
      })
      .catch(() => {});
  }, []);

  function pickTemplate(tmpl: (typeof AGENT_TEMPLATES)[number]) {
    setSelectedTemplate(tmpl);
    setConfig((c) => ({
      ...c,
      system_prompt: tmpl.system_prompt,
      user_prompt: tmpl.user_prompt,
      tools: [...tmpl.tools],
      output_format: tmpl.output_format,
      name: tmpl.id === "custom" ? "" : tmpl.label,
    }));
    setStep("configure");
  }

  async function save() {
    if (!config.name.trim()) {
      window.alert("Give your bee a name");
      return;
    }
    setSaving(true);
    try {
      const sid = config.swarm_id?.trim();
      const data = await hivePostJson<DynamicCreateResponse>("agents/dynamic", {
        name: config.name.trim(),
        hive_tier: "worker",
        swarm_id: sid ? sid : null,
        system_prompt: config.system_prompt.trim() || "You are a helpful AI agent executing Queenswarm missions.",
        user_prompt_template: config.user_prompt.trim() || null,
        tools: config.tools,
        output_format: config.output_format,
        output_destination: config.output_destination,
        output_config: { ...config.output_config, spawned_from_template: selectedTemplate?.id ?? "custom" },
        schedule_type: config.schedule_value ? "interval" : "on_demand",
        schedule_value: config.schedule_value || null,
        agent_status: "idle",
      });
      router.push(`/agents/${encodeURIComponent(data.agent_id)}`);
    } catch (e) {
      window.alert(`Failed: ${e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 pb-24">
      <button
        type="button"
        onClick={() => (step === "configure" ? setStep("template") : router.back())}
        className="qs-btn qs-btn--ghost qs-btn--sm self-start"
      >
        ← {step === "configure" ? "Back to templates" : "Back"}
      </button>

      <header>
        <h1 className="font-[family-name:var(--font-poppins)] text-2xl font-bold text-[#fafafa]">Spawn agent</h1>
        <p className="mt-2 font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
          {step === "template" ? "Choose a hive template." : "Wire prompts, tools, and rhythm."}
        </p>
      </header>

      {step === "template" ? (
        <div className="flex flex-col gap-3">
          {AGENT_TEMPLATES.map((tmpl) => (
            <button
              key={tmpl.id}
              type="button"
              onClick={() => pickTemplate(tmpl)}
              className={cn(
                "w-full rounded-3xl bg-black/35 p-4 text-left transition",
                tmpl.id === "custom"
                  ? "qs-rim hover:border-[color:rgb(255_184_0_/_0.35)]"
                  : "qs-rim-cyan-soft hover:border-[color:rgb(255_184_0_/_0.35)] hover:shadow-[0_0_20px_rgb(255_184_0/0.15)]",
              )}
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{tmpl.emoji}</span>
                <div className="min-w-0 flex-1 text-left">
                  <div className="font-semibold text-[#fafafa]">{tmpl.label}</div>
                  <div className="mt-1 line-clamp-2 text-xs text-zinc-500">{tmpl.system_prompt || "Blank canvas"}</div>
                  {tmpl.tools.length ? (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {tmpl.tools.map((t) => (
                        <span key={t} className="rounded bg-black/40 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
                          {t}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
                <span className="text-zinc-500">→</span>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <>
          <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
            <label className="qs-label">
              Bee name
            </label>
            <input
              value={config.name}
              onChange={(e) => setConfig((c) => ({ ...c, name: e.target.value }))}
              className="mt-2 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-pollen/40"
            />
          </section>

          <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
            <label className="qs-label">
              Manager / Swarm
            </label>
            <p className="mt-1 font-[family-name:var(--font-poppins)] text-xs text-zinc-600">
              Anchor this bee under a colony, or leave unassigned.
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <button
                type="button"
                onClick={() => setConfig((c) => ({ ...c, swarm_id: "" }))}
                className={cn(
                  "flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition",
                  !config.swarm_id
                    ? "border-pollen/50 bg-pollen/[0.08] text-pollen"
                    : "border-white/10 bg-[#141424] text-zinc-400 hover:border-white/18",
                )}
              >
                <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-zinc-600" aria-hidden />
                <span>No manager — unassigned</span>
              </button>

              {swarms
                .filter((s) => s.is_active !== false && !String(s.name).includes("__inactive_"))
                .map((s) => {
                  const accent = swarmAccentHex(s);
                  const sel = config.swarm_id === s.id;
                  return (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setConfig((c) => ({ ...c, swarm_id: s.id }))}
                      className={cn(
                        "flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition",
                        sel
                          ? "bg-black/55"
                          : "border-white/10 bg-[#141424] text-zinc-400 hover:border-white/18",
                      )}
                      style={
                        sel
                          ? {
                              borderColor: `${accent}77`,
                              backgroundColor: `${accent}14`,
                              color: accent,
                            }
                          : { borderColor: "rgb(255 255 255 / 0.1)" }
                      }
                    >
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full shadow-[0_0_10px_rgb(255_184_0/0.35)]"
                        style={{ backgroundColor: accent }}
                        aria-hidden
                      />
                      <div className="min-w-0 flex-1">
                        <div className={cn("font-semibold text-[#fafafa]", sel && "text-inherit")}>{s.name}</div>
                        <div className="text-[11px] text-zinc-500">
                          {swarmDisplayRole(s)} · {s.member_count ?? 0} bees
                        </div>
                      </div>
                      {sel ? <span className="font-mono text-xs">✓</span> : null}
                    </button>
                  );
                })}

              {swarms.filter((s) => s.is_active !== false && !String(s.name).includes("__inactive_")).length === 0 ? (
                <div className="rounded-xl px-3 py-2 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
                  No swarms yet —{" "}
                  <Link href="/swarms" className="font-semibold text-pollen underline-offset-2 hover:underline">
                    create one first
                  </Link>
                  .
                </div>
              ) : null}
            </div>
          </section>

          <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
            <label className="qs-label">
              System prompt
            </label>
            <textarea
              rows={5}
              value={config.system_prompt}
              onChange={(e) => setConfig((c) => ({ ...c, system_prompt: e.target.value }))}
              className="mt-2 w-full resize-y rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-cyan/30"
            />
            <label className="mt-4 qs-label">
              Task template
            </label>
            <textarea
              rows={3}
              value={config.user_prompt}
              onChange={(e) => setConfig((c) => ({ ...c, user_prompt: e.target.value }))}
              className="mt-2 w-full resize-y rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-cyan/30"
            />
          </section>

          <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
            <p className="qs-label">Tools</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {ALL_TOOLS.map((tool) => {
                const on = config.tools.includes(tool.id);
                return (
                  <button
                    key={tool.id}
                    type="button"
                    onClick={() =>
                      setConfig((c) => ({
                        ...c,
                        tools: on ? c.tools.filter((t) => t !== tool.id) : [...c.tools, tool.id],
                      }))
                    }
                    className={`rounded-xl border px-3 py-2 text-left text-xs transition ${
                      on ? "border-pollen/50 bg-pollen/[0.08] text-pollen" : "border-white/10 bg-black/40 text-zinc-400 hover:border-white/20"
                    }`}
                  >
                    <div className="font-semibold">{tool.label}</div>
                    <div className="mt-1 text-[10px] text-zinc-500">{tool.desc}</div>
                  </button>
                );
              })}
            </div>
          </section>

          <div className="grid gap-4 md:grid-cols-2">
            <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
              <p className="qs-label">Output</p>
              <div className="mt-3 flex flex-col gap-2">
                {OUTPUT_FORMATS.map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setConfig((c) => ({ ...c, output_format: f.id }))}
                    className={`rounded-xl border px-3 py-2 text-left text-sm ${
                      config.output_format === f.id
                        ? "border-success/50 bg-success/[0.08] text-success"
                        : "border-white/10 bg-transparent text-zinc-400 hover:border-success/40"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </section>
            <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
              <p className="qs-label">Schedule</p>
              <div className="mt-3 flex flex-col gap-2">
                {SCHEDULE_PRESETS.map((s) => (
                  <button
                    key={s.label}
                    type="button"
                    onClick={() => setConfig((c) => ({ ...c, schedule_value: s.value }))}
                    className={`rounded-xl border px-3 py-2 text-left text-sm ${
                      config.schedule_value === s.value
                        ? "border-cyan/50 bg-cyan/[0.08] text-cyan"
                        : "border-white/10 bg-transparent text-zinc-400 hover:border-cyan/40"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </section>
          </div>

          <button
            type="button"
            disabled={saving || !config.name.trim()}
            onClick={() => void save()}
            className="w-full rounded-xl border-2 border-pollen bg-pollen py-4 font-[family-name:var(--font-poppins)] text-sm font-bold text-black shadow-[0_0_32px_rgb(255_184_0/0.35)] disabled:opacity-45"
          >
            {saving ? "Spawning…" : "Spawn agent"}
          </button>
        </>
      )}
    </div>
  );
}

export default function NewAgentPage() {
  return (
    <Suspense
      fallback={<div className="flex min-h-[40vh] items-center justify-center text-sm text-muted-foreground">Loading…</div>}
    >
      <NewAgentWizardInner />
    </Suspense>
  );
}
