import { StatusIndicator } from "@/components/ui/status-indicator";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { LlmProvidersStatus } from "@/lib/hive-dashboard-session";

export const dynamic = "force-dynamic";

export default async function SettingsLlmKeysPage() {
  const status = await hiveServerRawJson<LlmProvidersStatus>("/auth/integrations/llm-providers");

  const rows: {
    key: keyof LlmProvidersStatus;
    title: string;
    role: string;
  }[] = [
    { key: "grok_configured", title: "Grok · xAI", role: "Route · primary" },
    { key: "anthropic_configured", title: "Claude · Anthropic", role: "Route · fallback" },
    { key: "openai_configured", title: "OpenAI · GPT-*", role: "Route · simulations / mini" },
  ];

  const offline = (
    <p className="mt-8 rounded-xl border border-alert/40 bg-black/35 p-4 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
      Nepodarilo sa načítať /auth/integrations/llm-providers — skontroluj INTERNAL_BACKEND_ORIGIN alebo Bearer proxy.
    </p>
  );

  return (
    <article className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-6 md:p-8">
      <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
        LLM provider keys
      </h2>
      <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
        Stav len z Hive env LiteLLM (žiadny export hodnôt klúčov).
      </p>
      {!status ? offline : (
        <ul className="mt-8 divide-y divide-cyan/[0.08]">
          {rows.map((row) => {
            const configured = !!status[row.key];
            return (
              <li key={row.key} className="flex flex-col gap-4 py-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-[family-name:var(--font-space-grotesk)] text-[#fafafa]">{row.title}</p>
                  <p className="mt-0.5 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">{row.role}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-2 rounded-full border border-cyan/[0.15] bg-black/40 px-3 py-1">
                    <StatusIndicator tone={configured ? "online" : "idle"} label={configured ? "Configured" : "Missing"} />
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </article>
  );
}
