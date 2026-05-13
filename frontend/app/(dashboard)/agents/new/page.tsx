"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { hivePostJson } from "@/lib/api";

const TEMPLATES = [
  {
    name: "Crypto Scout",
    system_prompt:
      "You are a crypto market analyst. Monitor token prices, sentiment, and news. Provide clear buy/hold/sell signals with confidence scores.",
    user_prompt_template:
      "Analyze current market conditions for the configured coin. Provide: 1) Current price & 24h change 2) Market sentiment 3) Key signals 4) Recommendation with confidence %",
    tools: ["coingecko", "youtube", "web_search"],
    output_format: "markdown",
    output_destination: "dashboard",
    schedule_value: "every 4 hours",
  },
  {
    name: "Blog Writer",
    system_prompt:
      "You are an SEO content writer for an e-commerce brand. Write engaging, optimized blog posts that drive organic traffic.",
    user_prompt_template:
      "Write a 400-word SEO blog post about the topic. Include title, meta description, subheadings, CTA. Use markdown.",
    tools: ["web_search", "wikipedia"],
    output_format: "markdown",
    output_destination: "dashboard",
    schedule_value: "",
  },
  {
    name: "Instagram Manager",
    system_prompt:
      "You are a social media manager specializing in Instagram. Create captions and hashtags that maximize reach.",
    user_prompt_template:
      "Create 3 Instagram variations for the product/topic with caption (max 150 chars), hashtags, CTA.",
    tools: ["web_search"],
    output_format: "text",
    output_destination: "dashboard",
    schedule_value: "",
  },
  {
    name: "News Digest",
    system_prompt: "You are a news curator. Summarize RSS headlines into a concise briefing.",
    user_prompt_template: "Summarize the top five stories from the RSS feed as bullet points.",
    tools: ["rss"],
    output_format: "markdown",
    output_destination: "dashboard",
    schedule_value: "daily 08:00",
  },
  {
    name: "Custom Agent",
    system_prompt: "",
    user_prompt_template: "",
    tools: [] as string[],
    output_format: "text",
    output_destination: "dashboard",
    schedule_value: "",
  },
] as const;

interface DynamicCreateResponse {
  agent_id: string;
  agent_name: string;
  config_id: string;
}

export default function NewAgentPage() {
  const router = useRouter();
  const [selected, setSelected] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  async function create() {
    if (!name.trim()) {
      window.alert("Give your bee a name.");
      return;
    }
    if (selected === null) {
      window.alert("Pick a template.");
      return;
    }
    setCreating(true);
    const tmpl = TEMPLATES[selected];
    try {
      const data = await hivePostJson<DynamicCreateResponse>("agents/dynamic", {
        name,
        system_prompt: tmpl.system_prompt || "You are a helpful AI agent.",
        user_prompt_template: tmpl.user_prompt_template || null,
        tools: [...tmpl.tools],
        output_format: tmpl.output_format,
        output_destination: tmpl.output_destination,
        output_config: {},
        schedule_type: tmpl.schedule_value ? "interval" : "on_demand",
        schedule_value: tmpl.schedule_value || null,
      });
      router.push(`/agents/${encodeURIComponent(data.agent_id)}/edit`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to create bee";
      window.alert(msg);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-2xl font-bold text-[#fafafa]">
          Create new bee
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Templates seed the universal executor; refine everything on the editor screen.
        </p>
      </div>

      <div className="space-y-3">
        {TEMPLATES.map((t, i) => (
          <button
            type="button"
            key={t.name}
            onClick={() => {
              setSelected(i);
              if (!name && t.name !== "Custom Agent") {
                setName(t.name);
              }
            }}
            className={`w-full rounded-xl border p-4 text-left transition-colors ${
              selected === i
                ? "border-pollen/[0.45] bg-pollen/[0.08]"
                : "border-[#1a1a3e] bg-hive-card/80 hover:border-gray-600"
            }`}
          >
            <div className={`text-sm font-semibold ${selected === i ? "text-pollen" : "text-[#fafafa]"}`}>{t.name}</div>
            <p className="mt-1 line-clamp-2 text-xs text-zinc-500">
              {t.system_prompt || "Blank canvas — define everything in the editor."}
            </p>
            {t.tools.length ? (
              <div className="mt-2 flex flex-wrap gap-1">
                {t.tools.map((tool) => (
                  <span key={tool} className="rounded bg-black/45 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
                    {tool}
                  </span>
                ))}
              </div>
            ) : null}
          </button>
        ))}
      </div>

      {selected !== null ? (
        <div className="rounded-xl border border-[#1a1a3e] bg-hive-card/70 p-4">
          <label className="mb-2 block text-xs uppercase tracking-wider text-zinc-500">Bee name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-[#1a1a3e] bg-[#050510] p-3 font-mono text-sm text-white focus:border-[#FFB800] focus:outline-none"
            placeholder="My ACKIE Scout"
            autoFocus
          />
        </div>
      ) : null}

      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => router.back()}
          className="rounded-xl border border-[#1a1a3e] px-6 py-3 text-sm text-gray-400 hover:border-gray-600"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() => void create()}
          disabled={creating || selected === null}
          className="flex-1 rounded-xl bg-pollen py-3 font-[family-name:var(--font-space-grotesk)] font-bold text-black shadow-[0_0_20px_#FFB80044] disabled:opacity-40"
        >
          {creating ? "Creating…" : "Create bee → edit"}
        </button>
      </div>
    </div>
  );
}
