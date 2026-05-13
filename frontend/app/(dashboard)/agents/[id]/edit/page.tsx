"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";

const TOOLS_AVAILABLE = [
  { id: "web_search", label: "Web Search", desc: "DuckDuckGo (free)" },
  { id: "youtube", label: "YouTube", desc: "Video search (needs API key)" },
  { id: "coingecko", label: "CoinGecko", desc: "Prices (free tier)" },
  { id: "rss", label: "RSS", desc: "Feeds" },
  { id: "scrape_url", label: "Scrape URL", desc: "Extract page text" },
  { id: "wikipedia", label: "Wikipedia", desc: "Summaries (free)" },
] as const;

const OUTPUT_FORMATS = [
  { id: "text", label: "Plain Text" },
  { id: "markdown", label: "Markdown" },
  { id: "json", label: "JSON" },
  { id: "excel", label: "Excel" },
  { id: "csv", label: "CSV" },
  { id: "html", label: "HTML" },
] as const;

const OUTPUT_DESTINATIONS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "email", label: "Email" },
  { id: "slack", label: "Slack" },
  { id: "file", label: "File" },
] as const;

interface AgentRow {
  id: string;
  name: string;
}

interface BeeConfigState {
  system_prompt: string;
  user_prompt_template: string;
  tools: string[];
  output_format: string;
  output_destination: string;
  output_config: Record<string, string>;
  schedule_type: string;
  schedule_value: string;
}

const inputCls =
  "w-full rounded-lg border border-[#1a1a3e] bg-[#050510] p-3 font-mono text-sm text-white focus:border-[#FFB800] focus:outline-none";

const labelCls = "mb-2 block text-xs uppercase tracking-wider text-gray-400";

const sectionCls = "space-y-4 rounded-xl border border-[#1a1a3e] bg-[#0d0d2b] p-5";

export default function AgentEditPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [testOutput, setTestOutput] = useState("");
  const [testingPrompt, setTestingPrompt] = useState(false);
  const [agent, setAgent] = useState<AgentRow | null>(null);
  const [cfg, setCfg] = useState<BeeConfigState>({
    system_prompt: "",
    user_prompt_template: "",
    tools: [],
    output_format: "text",
    output_destination: "dashboard",
    output_config: {},
    schedule_type: "on_demand",
    schedule_value: "",
  });

  const loadData = useCallback(async () => {
    if (!id) {
      return;
    }
    try {
      const agentData = await hiveGet<AgentRow>(`agents/${encodeURIComponent(id)}`);
      setAgent(agentData);
      try {
        const cfgRow = await hiveGet<Record<string, unknown>>(`agents/${encodeURIComponent(id)}/config`);
        setCfg({
          system_prompt: String(cfgRow.system_prompt ?? ""),
          user_prompt_template: cfgRow.user_prompt_template == null ? "" : String(cfgRow.user_prompt_template),
          tools: Array.isArray(cfgRow.tools) ? (cfgRow.tools as string[]) : [],
          output_format: String(cfgRow.output_format ?? "text"),
          output_destination: String(cfgRow.output_destination ?? "dashboard"),
          output_config: typeof cfgRow.output_config === "object" && cfgRow.output_config !== null
            ? Object.fromEntries(
                Object.entries(cfgRow.output_config as Record<string, unknown>).map(([k, v]) => [
                  k,
                  v == null ? "" : String(v),
                ]),
              )
            : {},
          schedule_type: String(cfgRow.schedule_type ?? "on_demand"),
          schedule_value: cfgRow.schedule_value == null ? "" : String(cfgRow.schedule_value),
        });
      } catch (e) {
        if (e instanceof HiveApiError && e.status === 404) {
          /* first-time editor; seed empty */
        } else {
          throw e;
        }
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function save() {
    setSaving(true);
    try {
      await hivePutJson(`agents/${encodeURIComponent(id)}/config`, {
        system_prompt: cfg.system_prompt || "You are a helpful AI agent.",
        user_prompt_template: cfg.user_prompt_template || null,
        tools: cfg.tools,
        output_format: cfg.output_format,
        output_destination: cfg.output_destination,
        output_config: cfg.output_config,
        schedule_type: cfg.schedule_type,
        schedule_value: cfg.schedule_value || null,
        is_active: true,
      });
      router.push(`/agents/${encodeURIComponent(id)}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Save failed";
      window.alert(msg);
    } finally {
      setSaving(false);
    }
  }

  async function runNow(): Promise<void> {
    setRunning(true);
    try {
      const data = await hivePostJson<{ task_id: string }>(`agents/${encodeURIComponent(id)}/run`, {});
      window.alert(`Task queued: ${data.task_id}\nCheck Tasks for output.`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Run failed";
      window.alert(msg);
    } finally {
      setRunning(false);
    }
  }

  async function testPrompt(): Promise<void> {
    setTestingPrompt(true);
    setTestOutput("");
    try {
      const overlay: Record<string, unknown> = {
        tools: cfg.tools,
        output_format: cfg.output_format,
        output_destination: cfg.output_destination,
        output_config: cfg.output_config,
      };
      const sp = cfg.system_prompt.trim();
      if (sp.length) {
        overlay.system_prompt = cfg.system_prompt;
      }
      const up = cfg.user_prompt_template.trim();
      if (up.length) {
        overlay.user_prompt_template = cfg.user_prompt_template;
      }
      const payload = await hivePostJson<{ task_id: string }>(`agents/${encodeURIComponent(id)}/run`, overlay);
      const taskId = String(payload.task_id);
      for (let i = 0; i < 30; i += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        const ledger = await hiveGet<{
          status: string;
          result?: Record<string, unknown> | string | null;
          error_msg?: string | null;
        }>(`tasks/${encodeURIComponent(taskId)}`);
        const st = (ledger.status ?? "").toLowerCase();
        if (st === "completed" || st === "failed") {
          const res = ledger.result;
          const snippet =
            typeof res === "string"
              ? res
              : res && typeof res === "object" && "output" in res && typeof res.output !== "undefined"
                ? typeof res.output === "string"
                  ? res.output
                  : JSON.stringify(res.output, null, 2)
                : JSON.stringify(res, null, 2);
          setTestOutput(st === "failed" ? String(ledger.error_msg ?? snippet) : snippet);
          break;
        }
        setTestOutput(`🐝 Running… (${String((i + 1) * 2)}s)`);
      }
    } catch (e: unknown) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : String(e);
      setTestOutput(`Error: ${msg}`);
    } finally {
      setTestingPrompt(false);
    }
  }

  function toggleTool(toolId: string) {
    setCfg((c) => ({
      ...c,
      tools: c.tools.includes(toolId) ? c.tools.filter((t) => t !== toolId) : [...c.tools, toolId],
    }));
  }

  if (loading) {
    return <div className="p-8 font-mono animate-pulse text-pollen">Loading bee config…</div>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-space-grotesk)] text-2xl font-bold text-[#fafafa]">
            🐝 {agent?.name ?? id}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Configure prompts, tools, routing, and schedules for the universal executor.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void runNow()}
            disabled={running}
            className="rounded-lg border border-cyan/[0.35] bg-cyan/[0.08] px-4 py-2 font-mono text-sm text-cyan hover:bg-cyan/[0.14] disabled:opacity-50"
          >
            {running ? "Running…" : "Run now"}
          </button>
          <button
            type="button"
            onClick={() => void save()}
            disabled={saving}
            className="rounded-lg bg-pollen px-4 py-2 text-sm font-semibold text-black hover:opacity-95 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save config"}
          </button>
        </div>
      </div>

      <div className={sectionCls}>
        <label className={labelCls}>System prompt</label>
        <textarea
          value={cfg.system_prompt}
          onChange={(e) => setCfg((c) => ({ ...c, system_prompt: e.target.value }))}
          rows={5}
          className={`${inputCls} resize-y`}
          placeholder="Who this bee is."
        />
        <label className={labelCls}>User prompt template</label>
        <textarea
          value={cfg.user_prompt_template}
          onChange={(e) => setCfg((c) => ({ ...c, user_prompt_template: e.target.value }))}
          rows={3}
          className={`${inputCls} resize-y`}
          placeholder="What to do each run."
        />
      </div>

      <div className={sectionCls}>
        <label className={labelCls}>Tools</label>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {TOOLS_AVAILABLE.map((tool) => {
            const active = cfg.tools.includes(tool.id);
            return (
              <button
                type="button"
                key={tool.id}
                onClick={() => toggleTool(tool.id)}
                className={`rounded-lg border p-3 text-left text-sm transition-colors ${
                  active
                    ? "border-pollen/[0.4] bg-pollen/[0.08] text-pollen"
                    : "border-[#1a1a3e] bg-[#050510] text-gray-400 hover:border-gray-600"
                }`}
              >
                <div className="font-medium">{tool.label}</div>
                <div className="mt-0.5 text-xs opacity-60">{tool.desc}</div>
              </button>
            );
          })}
        </div>
        {cfg.tools.includes("rss") ? (
          <div>
            <label className={labelCls}>RSS URL</label>
            <input
              value={cfg.output_config.rss_url ?? ""}
              onChange={(e) =>
                setCfg((c) => ({
                  ...c,
                  output_config: { ...c.output_config, rss_url: e.target.value },
                }))
              }
              className={inputCls}
              placeholder="https://feeds.bbci.co.uk/news/rss.xml"
            />
          </div>
        ) : null}
        {cfg.tools.includes("scrape_url") ? (
          <div>
            <label className={labelCls}>URL to scrape</label>
            <input
              value={cfg.output_config.scrape_url ?? ""}
              onChange={(e) =>
                setCfg((c) => ({
                  ...c,
                  output_config: { ...c.output_config, scrape_url: e.target.value },
                }))
              }
              className={inputCls}
              placeholder="https://example.com"
            />
          </div>
        ) : null}
        {cfg.tools.includes("coingecko") ? (
          <div>
            <label className={labelCls}>CoinGecko coin id</label>
            <input
              value={cfg.output_config.coingecko_coin_id ?? "bitcoin"}
              onChange={(e) =>
                setCfg((c) => ({
                  ...c,
                  output_config: { ...c.output_config, coingecko_coin_id: e.target.value },
                }))
              }
              className={inputCls}
              placeholder="bitcoin"
            />
          </div>
        ) : null}
      </div>

      <div className={sectionCls}>
        <label className={labelCls}>Output format</label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {OUTPUT_FORMATS.map((fmt) => (
            <button
              type="button"
              key={fmt.id}
              onClick={() => setCfg((c) => ({ ...c, output_format: fmt.id }))}
              className={`rounded-lg border p-3 text-left text-sm ${
                cfg.output_format === fmt.id
                  ? "border-success/45 bg-success/10 text-success"
                  : "border-[#1a1a3e] bg-[#050510] text-gray-400 hover:border-gray-600"
              }`}
            >
              {fmt.label}
            </button>
          ))}
        </div>
      </div>

      <div className={sectionCls}>
        <label className={labelCls}>Output destination</label>
        <div className="mb-4 grid grid-cols-2 gap-2">
          {OUTPUT_DESTINATIONS.map((dest) => (
            <button
              type="button"
              key={dest.id}
              onClick={() => setCfg((c) => ({ ...c, output_destination: dest.id }))}
              className={`rounded-lg border p-3 text-left text-sm ${
                cfg.output_destination === dest.id
                  ? "border-alert/45 bg-alert/10 text-alert"
                  : "border-[#1a1a3e] bg-[#050510] text-gray-400 hover:border-gray-600"
              }`}
            >
              {dest.label}
            </button>
          ))}
        </div>
        {cfg.output_destination === "email" ? (
          <div className="space-y-3">
            <div>
              <label className={labelCls}>Email to</label>
              <input
                value={cfg.output_config.email_to ?? ""}
                onChange={(e) =>
                  setCfg((c) => ({
                    ...c,
                    output_config: { ...c.output_config, email_to: e.target.value },
                  }))
                }
                className={inputCls}
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className={labelCls}>Subject</label>
              <input
                value={cfg.output_config.email_subject ?? ""}
                onChange={(e) =>
                  setCfg((c) => ({
                    ...c,
                    output_config: { ...c.output_config, email_subject: e.target.value },
                  }))
                }
                className={inputCls}
                placeholder="Daily report"
              />
            </div>
          </div>
        ) : null}
        {cfg.output_destination === "slack" ? (
          <div className="space-y-3">
            <div>
              <label className={labelCls}>Slack webhook</label>
              <input
                value={cfg.output_config.slack_webhook ?? ""}
                onChange={(e) =>
                  setCfg((c) => ({
                    ...c,
                    output_config: { ...c.output_config, slack_webhook: e.target.value },
                  }))
                }
                className={inputCls}
                placeholder="https://hooks.slack.com/..."
              />
            </div>
            <div>
              <label className={labelCls}>Channel</label>
              <input
                value={cfg.output_config.slack_channel ?? ""}
                onChange={(e) =>
                  setCfg((c) => ({
                    ...c,
                    output_config: { ...c.output_config, slack_channel: e.target.value },
                  }))
                }
                className={inputCls}
                placeholder="#marketing"
              />
            </div>
          </div>
        ) : null}
        {cfg.output_destination === "file" ? (
          <div>
            <label className={labelCls}>Filename template</label>
            <input
              value={cfg.output_config.filename_template ?? ""}
              onChange={(e) =>
                setCfg((c) => ({
                  ...c,
                  output_config: { ...c.output_config, filename_template: e.target.value },
                }))
              }
              className={inputCls}
              placeholder="report_{date}.xlsx"
            />
          </div>
        ) : null}
      </div>

      <div className={sectionCls}>
        <label className={labelCls}>Schedule</label>
        <input
          value={cfg.schedule_value}
          onChange={(e) => {
            const raw = e.target.value;
            const trimmed = raw.trim();
            const kind =
              trimmed.length === 0
                ? "on_demand"
                : trimmed.split(/\s+/).length >= 5
                  ? "cron"
                  : "interval";
            setCfg((c) => ({
              ...c,
              schedule_value: raw,
              schedule_type: kind,
            }));
          }}
          className={inputCls}
          placeholder='e.g. "every 4 hours", "daily 08:00", or cron "0 */4 * * *"'
        />
        <p className="mt-2 font-mono text-xs text-zinc-500">
          Type <span className="text-cyan">on_demand</span> by clearing the field. Use interval/cron types from the API
          when automating with Beat.
        </p>
      </div>

      <div className={sectionCls}>
        <div className="mb-3 flex items-center justify-between">
          <label className={labelCls}>🧪 Test prompt</label>
          <button
            type="button"
            onClick={() => void testPrompt()}
            disabled={testingPrompt}
            className="rounded-lg border border-data/35 bg-data/10 px-4 py-1.5 font-mono text-xs text-data transition hover:bg-data/18 disabled:opacity-50"
          >
            {testingPrompt ? "Running…" : "▶ Run test"}
          </button>
        </div>
        {testOutput ? (
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-xl border border-cyan/[0.12] bg-[#050510] p-4 font-mono text-xs text-zinc-200">
            {testOutput}
          </pre>
        ) : (
          <p className="text-xs text-zinc-600">
            Run once with overlay prompts + tools above — persists only inside the backlog until you explicitly save agent
            config.
          </p>
        )}
      </div>

      <div className="flex gap-3 pt-2">
        <Link
          href={`/agents/${encodeURIComponent(id)}`}
          className="rounded-xl border border-[#1a1a3e] px-6 py-3 text-sm text-gray-400 hover:border-gray-600"
        >
          Cancel
        </Link>
        <button
          type="button"
          onClick={() => void save()}
          disabled={saving}
          className="flex-1 rounded-xl bg-pollen py-3 font-[family-name:var(--font-space-grotesk)] font-bold text-black shadow-[0_0_20px_#FFB80044] hover:opacity-95 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save agent config"}
        </button>
      </div>
    </div>
  );
}
