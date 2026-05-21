"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { PencilIcon, XIcon } from "lucide-react";

import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import { cn } from "@/lib/utils";
import { InfoHint } from "@/components/hive/info-hint";

const ALL_TOOLS = [
  { id: "web_search", label: "Web Search", desc: "Search index (DuckDuckGo-style)" },
  { id: "youtube", label: "YouTube", desc: "Requires API credentials when enabled" },
  { id: "coingecko", label: "CoinGecko", desc: "Pricing feeds" },
  { id: "rss", label: "RSS", desc: "Feeds" },
  { id: "scrape_url", label: "Scrape URL", desc: "Fetched pages" },
  { id: "wikipedia", label: "Wikipedia", desc: "Article summaries" },
] as const;

const EMOJI_OPTIONS = ["🐝", "📊", "✍️", "📸", "📰", "🧠", "⚡", "🔍", "🧩", "🚀", "🎯", "🛠️"] as const;

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

function configureOptionClass(
  active: boolean,
  tone: "cyan" | "pollen" | "success" = "cyan",
  size: "sm" | "xs" = "sm",
): string {
  const activeTone =
    tone === "pollen"
      ? "border-pollen/40 bg-pollen/10 text-pollen"
      : tone === "success"
        ? "border-(--qs-green)/40 bg-(--qs-green)/10 text-(--qs-green)"
        : "border-(--qs-cyan)/40 bg-(--qs-cyan)/10 text-(--qs-cyan)";

  return cn(
    "w-full rounded-xl border px-3 py-2 text-left transition",
    size === "xs" ? "text-xs" : "text-sm",
    active
      ? activeTone
      : "border-(--qs-border) bg-black/25 text-(--qs-text-3) hover:border-(--qs-border-2) hover:text-(--qs-text-2)",
  );
}

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

interface AgentTemplate {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  tools: string[];
  prompt_template: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

interface TeamOverviewResponse {
  tenant_role: string;
}

interface TemplateFormValue {
  name: string;
  description: string;
  icon: string;
  category: string;
  tools: string[];
  prompt_template: string;
  is_default: boolean;
}

interface TemplateModalProps {
  open: boolean;
  mode: "create" | "edit";
  value: TemplateFormValue;
  isAdmin: boolean;
  saving: boolean;
  onClose: () => void;
  onChange: (next: TemplateFormValue) => void;
  onSubmit: () => Promise<void>;
}

function createEmptyTemplateForm(): TemplateFormValue {
  return {
    name: "",
    description: "",
    icon: "🐝",
    category: "general",
    tools: [],
    prompt_template: "",
    is_default: false,
  };
}

function TemplateEditorModal({
  open,
  mode,
  value,
  isAdmin,
  saving,
  onClose,
  onChange,
  onSubmit,
}: TemplateModalProps) {
  if (!open) return null;
  const title = mode === "create" ? "Create template" : "Edit template";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4" onClick={onClose} role="presentation">
      <div
        role="dialog"
        aria-label={title}
        className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-cyan/30 bg-[#070d16] p-5 shadow-[0_0_40px_rgba(0,255,255,0.12)]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#fafafa]">{title}</h2>
          <button type="button" onClick={onClose} className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-zinc-300 hover:border-white/30">
            Close
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <section className="space-y-3 rounded-xl border border-white/10 bg-black/25 p-3">
            <label className="qs-label">Názov</label>
            <input
              value={value.name}
              onChange={(event) => onChange({ ...value, name: event.target.value })}
              className="w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-white outline-none focus:border-pollen/50"
              placeholder="Crypto Scout"
            />

            <label className="qs-label">Popis</label>
            <textarea
              rows={4}
              value={value.description}
              onChange={(event) => onChange({ ...value, description: event.target.value })}
              className="w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-white outline-none focus:border-pollen/50"
              placeholder="What this template is optimized for..."
            />

            <label className="qs-label">Kategória</label>
            <input
              value={value.category}
              onChange={(event) => onChange({ ...value, category: event.target.value })}
              className="w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-white outline-none focus:border-pollen/50"
              placeholder="research"
            />
          </section>

          <section className="space-y-3 rounded-xl border border-white/10 bg-black/25 p-3">
            <label className="qs-label">Ikona (emoji picker)</label>
            <div className="grid grid-cols-6 gap-2">
              {EMOJI_OPTIONS.map((emoji) => (
                <button
                  key={emoji}
                  type="button"
                  onClick={() => onChange({ ...value, icon: emoji })}
                  className={cn(
                    "rounded-lg border px-2 py-2 text-xl transition",
                    value.icon === emoji
                      ? "border-pollen/60 bg-pollen/12"
                      : "border-white/10 bg-black/35 hover:border-white/25",
                  )}
                >
                  {emoji}
                </button>
              ))}
            </div>

            <label className="qs-label">Tools (multi-select)</label>
            <div className="grid gap-2 sm:grid-cols-2">
              {ALL_TOOLS.map((tool) => {
                const selected = value.tools.includes(tool.id);
                return (
                  <button
                    key={tool.id}
                    type="button"
                    onClick={() =>
                      onChange({
                        ...value,
                        tools: selected ? value.tools.filter((item) => item !== tool.id) : [...value.tools, tool.id],
                      })
                    }
                    className={cn(
                      "rounded-lg border px-3 py-2 text-left text-xs transition",
                      selected
                        ? "border-cyan/60 bg-cyan/[0.10] text-cyan"
                        : "border-white/10 bg-black/35 text-zinc-400 hover:border-white/25",
                    )}
                  >
                    <div className="font-semibold">{tool.label}</div>
                    <div className="mt-0.5 text-[10px] text-zinc-500">{tool.desc}</div>
                  </button>
                );
              })}
            </div>
          </section>
        </div>

        <section className="mt-4 space-y-2 rounded-xl border border-white/10 bg-black/25 p-3">
          <label className="qs-label">Prompt template</label>
          <textarea
            rows={6}
            value={value.prompt_template}
            onChange={(event) => onChange({ ...value, prompt_template: event.target.value })}
            className="w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-white outline-none focus:border-cyan/50"
            placeholder="You are a ..."
          />
        </section>

        <section className="mt-4 rounded-xl border border-white/10 bg-black/25 p-3">
          <label className="inline-flex items-center gap-2 text-sm text-zinc-200">
            <input
              type="checkbox"
              checked={value.is_default}
              disabled={!isAdmin}
              onChange={(event) => onChange({ ...value, is_default: event.target.checked })}
              className="h-4 w-4 rounded border border-white/20 bg-black/40"
            />
            Is default checkbox
          </label>
          {!isAdmin ? <p className="mt-1 text-xs text-zinc-500">Only admin can mark template as default.</p> : null}
        </section>

        <div className="mt-5 flex items-center justify-end gap-3">
          <button type="button" onClick={onClose} className="qs-btn qs-btn--ghost qs-btn--sm">
            Cancel
          </button>
          <button
            type="button"
            disabled={saving || !value.name.trim()}
            onClick={() => void onSubmit()}
            className="rounded-lg border border-pollen bg-pollen px-4 py-2 text-sm font-semibold text-black shadow-[0_0_18px_rgb(255_184_0/0.30)] disabled:opacity-45"
          >
            {saving ? "Saving…" : mode === "create" ? "Create template" : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
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
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<AgentTemplate | null>(null);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [tenantRole, setTenantRole] = useState("guest");
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [templateModalMode, setTemplateModalMode] = useState<"create" | "edit">("create");
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);
  const [templateForm, setTemplateForm] = useState<TemplateFormValue>(createEmptyTemplateForm());
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [deletingTemplateId, setDeletingTemplateId] = useState<string | null>(null);
  const [deleteTemplateTarget, setDeleteTemplateTarget] = useState<AgentTemplate | null>(null);
  const [swarms, setSwarms] = useState<SwarmLite[]>([]);
  const [saving, setSaving] = useState(false);

  const swarmParam = searchParams.get("swarm_id") ?? "";
  const canManageTemplates = tenantRole === "owner" || tenantRole === "admin";
  const isAdmin = tenantRole === "admin";

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

  const templatesByCategory = useMemo(() => {
    const grouped = new Map<string, AgentTemplate[]>();
    templates.forEach((template) => {
      const key = template.category.trim() || "general";
      const list = grouped.get(key) ?? [];
      list.push(template);
      grouped.set(key, list);
    });
    return Array.from(grouped.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [templates]);

  useEffect(() => {
    void hiveGet<TeamOverviewResponse>("settings/team")
      .then((overview) => setTenantRole(String(overview.tenant_role || "guest")))
      .catch(() => setTenantRole("guest"));
  }, []);

  async function refreshTemplates() {
    setLoadingTemplates(true);
    setTemplateError(null);
    try {
      const rows = await hiveGet<AgentTemplate[]>("agent-templates");
      setTemplates(rows);
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : error instanceof Error ? error.message : "Failed to load templates";
      setTemplateError(msg);
    } finally {
      setLoadingTemplates(false);
    }
  }

  useEffect(() => {
    void refreshTemplates();
  }, []);

  useEffect(() => {
    const editTemplateId = searchParams.get("editTemplate");
    if (!editTemplateId || !canManageTemplates || loadingTemplates) {
      return;
    }
    const match = templates.find((row) => row.id === editTemplateId);
    if (match) {
      openEditTemplateModal(match);
      router.replace("/agents/new", { scroll: false });
    }
  }, [searchParams, templates, canManageTemplates, loadingTemplates, router]);

  useEffect(() => {
    if (swarmParam) setConfig((prev) => ({ ...prev, swarm_id: swarmParam }));
  }, [swarmParam]);

  useEffect(() => {
    void hiveGet<unknown>("swarms?limit=200")
      .then((data) => {
        const rows = Array.isArray(data)
          ? data
          : Array.isArray((data as { items?: unknown }).items)
            ? (data as { items: unknown[] }).items
            : Array.isArray((data as { swarms?: unknown }).swarms)
              ? (data as { swarms: unknown[] }).swarms
              : [];
        setSwarms(
          rows
            .filter((item): item is SwarmLite => typeof item === "object" && item !== null && "id" in item && "name" in item)
            .map((item) => ({
              ...item,
              local_memory:
                item.local_memory && typeof item.local_memory === "object"
                  ? (item.local_memory as Record<string, unknown>)
                  : undefined,
            })),
        );
      })
      .catch(() => {});
  }, []);

  function pickTemplate(template: AgentTemplate | null) {
    setSelectedTemplate(template);
    setConfig((prev) => ({
      ...prev,
      name: template ? template.name : "",
      system_prompt: template?.prompt_template ?? "",
      user_prompt: "",
      tools: [...(template?.tools ?? [])],
      output_format: "text",
    }));
    setStep("configure");
  }

  function openCreateTemplateModal() {
    setTemplateModalMode("create");
    setEditingTemplateId(null);
    setTemplateForm(createEmptyTemplateForm());
    setTemplateModalOpen(true);
  }

  function openEditTemplateModal(template: AgentTemplate) {
    setTemplateModalMode("edit");
    setEditingTemplateId(template.id);
    setTemplateForm({
      name: template.name,
      description: template.description,
      icon: template.icon || "🐝",
      category: template.category,
      tools: [...template.tools],
      prompt_template: template.prompt_template,
      is_default: template.is_default,
    });
    setTemplateModalOpen(true);
  }

  async function submitTemplateModal() {
    if (!canManageTemplates) {
      window.alert("Only owner/admin can manage templates.");
      return;
    }
    setSavingTemplate(true);
    try {
      if (templateModalMode === "create") {
        await hivePostJson<AgentTemplate>("agent-templates", templateForm);
      } else if (editingTemplateId) {
        await hivePutJson<AgentTemplate>(`agent-templates/${encodeURIComponent(editingTemplateId)}`, templateForm);
      }
      setTemplateModalOpen(false);
      await refreshTemplates();
    } catch (error) {
      window.alert(`Template save failed: ${error instanceof HiveApiError ? error.message : error instanceof Error ? error.message : String(error)}`);
    } finally {
      setSavingTemplate(false);
    }
  }

  async function confirmDeleteTemplate() {
    if (!deleteTemplateTarget || !canManageTemplates) {
      return;
    }
    const templateId = deleteTemplateTarget.id;
    setDeletingTemplateId(templateId);
    try {
      await hiveDelete<void>(`agent-templates/${encodeURIComponent(templateId)}`);
      if (selectedTemplate?.id === templateId) {
        setSelectedTemplate(null);
      }
      setDeleteTemplateTarget(null);
      await refreshTemplates();
    } catch (error) {
      window.alert(`Template delete failed: ${error instanceof HiveApiError ? error.message : error instanceof Error ? error.message : String(error)}`);
    } finally {
      setDeletingTemplateId(null);
    }
  }

  async function saveAgent() {
    if (!config.name.trim()) {
      window.alert("Give your bee a name");
      return;
    }
    setSaving(true);
    try {
      let spawnTemplate = selectedTemplate;
      if (selectedTemplate?.id) {
        try {
          spawnTemplate = await hiveGet<AgentTemplate>(`agent-templates/${encodeURIComponent(selectedTemplate.id)}`);
        } catch {
          // Keep local selection as fallback so spawn flow remains usable.
        }
      }
      const sid = config.swarm_id?.trim();
      const data = await hivePostJson<DynamicCreateResponse>("agents/dynamic", {
        name: config.name.trim() || spawnTemplate?.name || "Worker Bee",
        hive_tier: "worker",
        swarm_id: sid ? sid : null,
        system_prompt:
          config.system_prompt.trim() ||
          spawnTemplate?.prompt_template ||
          "You are a helpful AI agent executing Queenswarm missions.",
        user_prompt_template: config.user_prompt.trim() || null,
        tools: config.tools.length ? config.tools : (spawnTemplate?.tools ?? []),
        output_format: config.output_format,
        output_destination: config.output_destination,
        output_config: {
          ...config.output_config,
          spawned_from_template: spawnTemplate?.id ?? "custom_manual",
          spawned_template_category: spawnTemplate?.category ?? "custom",
        },
        schedule_type: config.schedule_value ? "interval" : "on_demand",
        schedule_value: config.schedule_value || null,
        agent_status: "idle",
      });
      router.push(`/agents/${encodeURIComponent(data.agent_id)}`);
    } catch (error) {
      window.alert(`Failed: ${error instanceof HiveApiError ? error.message : error instanceof Error ? error.message : String(error)}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="v4-spawn-agent-shell mx-auto max-w-2xl space-y-6 pb-24">
      <TemplateEditorModal
        open={templateModalOpen}
        mode={templateModalMode}
        value={templateForm}
        isAdmin={isAdmin}
        saving={savingTemplate}
        onClose={() => setTemplateModalOpen(false)}
        onChange={setTemplateForm}
        onSubmit={submitTemplateModal}
      />

      <ConfirmModal
        open={deleteTemplateTarget !== null}
        title="Delete template?"
        message={
          deleteTemplateTarget
            ? `Remove “${deleteTemplateTarget.name}” from the tenant library. This cannot be undone.`
            : ""
        }
        confirmLabel="Delete"
        danger
        onConfirm={() => void confirmDeleteTemplate()}
        onCancel={() => setDeleteTemplateTarget(null)}
      />

      <button type="button" onClick={() => (step === "configure" ? setStep("template") : router.back())} className="qs-btn qs-btn--ghost qs-btn--sm self-start">
        ← {step === "configure" ? "Back to templates" : "Back"}
      </button>

      <header>
        <div className="flex items-center gap-2">
          <h1 className="font-(family-name:--font-poppins) text-2xl font-bold text-[#fafafa]">Spawn agent</h1>
          <InfoHint
            title="Spawn agent wizard"
            description="Creates a new bee agent and configures prompts, tools, output format, and schedule."
            options={["Template preset", "Swarm assignment", "Prompt and tool tuning", "Execution rhythm"]}
          />
        </div>
        <p className="mt-2 font-(family-name:--font-poppins) text-sm text-muted-foreground">
          {step === "template" ? "Choose or manage tenant templates." : "Wire prompts, tools, and rhythm."}
        </p>
        <div className="mt-2 flex items-center gap-3 text-xs text-zinc-500">
          <Link href="/agents" className="underline-offset-2 hover:text-zinc-300 hover:underline">
            Agents overview
          </Link>
          <span>•</span>
          <span>Template library is tenant-scoped</span>
        </div>
      </header>

      {step === "template" ? (
        <div className="space-y-4">
          <div className="v4-template-library-banner flex items-center justify-between gap-3 rounded-[var(--qs-radius-lg)] qs-rim bg-[var(--qs-surface)] px-4 py-4 backdrop-blur-sm">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-(--qs-text)">Template library</p>
              <p className="text-xs text-(--qs-text-3)">Create segments for your team and reuse them in one click.</p>
            </div>
            <button
              type="button"
              onClick={openCreateTemplateModal}
              disabled={!canManageTemplates}
              className="qs-btn qs-btn--primary qs-btn--sm shrink-0"
            >
              + Create new template
            </button>
          </div>

          <button
            type="button"
            onClick={() => pickTemplate(null)}
            className="w-full rounded-3xl qs-rim bg-black/35 p-4 text-left transition hover:border-[rgb(255_184_0/0.35)]"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">🐝</span>
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-[#fafafa]">Custom (blank)</div>
                <div className="mt-1 text-xs text-zinc-500">Start from an empty template and configure everything manually.</div>
              </div>
              <span className="text-zinc-500">→</span>
            </div>
          </button>

          {loadingTemplates ? <div className="rounded-2xl border border-[color:var(--qs-border)] px-4 py-5 text-sm text-zinc-500">Loading templates…</div> : null}
          {templateError ? <div className="rounded-2xl border border-red-500/30 bg-red-500/8 px-4 py-5 text-sm text-red-300">{templateError}</div> : null}

          {!loadingTemplates && !templateError ? (
            templates.length ? (
              <div className="space-y-4">
                {templatesByCategory.map(([category, entries]) => (
                  <section key={category} className="space-y-2">
                    <div className="text-xs uppercase tracking-[0.08em] text-zinc-500">{category}</div>
                    <div className="flex flex-col gap-3">
                      {entries.map((template) => (
                        <div key={template.id} className="relative">
                          {canManageTemplates ? (
                            <div className="absolute right-2 top-2 z-10 flex items-center gap-1.5">
                              <button
                                type="button"
                                aria-label={`Edit template ${template.name}`}
                                className="flex h-9 w-9 items-center justify-center rounded-lg border border-(--qs-border) bg-black/45 text-(--qs-text-2) transition hover:border-(--qs-border-2) hover:text-pollen touch-manipulation"
                                onClick={() => openEditTemplateModal(template)}
                              >
                                <PencilIcon className="h-4 w-4" aria-hidden strokeWidth={2.25} />
                              </button>
                              <button
                                type="button"
                                aria-label={`Delete template ${template.name}`}
                                disabled={deletingTemplateId === template.id}
                                className="flex h-9 w-9 items-center justify-center rounded-lg border border-danger/45 bg-danger/12 text-danger transition hover:border-danger hover:bg-danger/20 disabled:opacity-40 touch-manipulation"
                                onClick={() => setDeleteTemplateTarget(template)}
                              >
                                <XIcon className="h-4 w-4" aria-hidden strokeWidth={2.5} />
                              </button>
                            </div>
                          ) : null}
                          <div
                            className={cn(
                              "w-full rounded-3xl qs-rim bg-black/35 p-4 transition hover:border-[rgb(255_184_0/0.35)] hover:shadow-[0_0_20px_rgb(255_184_0/0.15)]",
                              canManageTemplates && "pt-12",
                            )}
                          >
                            <button type="button" onClick={() => pickTemplate(template)} className="flex w-full min-w-0 items-center gap-3 text-left">
                              <span className="text-2xl">{template.icon || "🐝"}</span>
                              <div className="min-w-0 flex-1">
                                <div className="font-semibold text-[#fafafa]">{template.name}</div>
                                <div className="mt-1 line-clamp-2 text-xs text-zinc-500">{template.description || "No description"}</div>
                                <div className="mt-2 flex flex-wrap items-center gap-1">
                                  {template.is_default ? (
                                    <span className="rounded bg-pollen/15 px-1.5 py-0.5 text-[10px] font-semibold text-pollen">default</span>
                                  ) : null}
                                  {template.tools.map((tool) => (
                                    <span key={tool} className="rounded bg-black/40 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
                                      {tool}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              <span className="text-zinc-500">→</span>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            ) : (
              <div className="v4-empty py-8 text-sm">No templates yet. Create your first one, or continue with a blank custom agent.</div>
            )
          ) : null}
          <div className="flex justify-center">
            <InfoHint
              title="Dynamic templates"
              description="Templates are now managed via API and shared across the active tenant."
              options={["Create/Edit/Delete template cards", "Use template as spawn preset", "RBAC protected template management"]}
            />
          </div>
        </div>
      ) : (
        <>
          {selectedTemplate ? (
            <div className="rounded-2xl border border-cyan/30 bg-cyan/[0.06] p-3 text-xs text-zinc-300">
              Spawning from template:{" "}
              <span className="font-semibold text-cyan">
                {selectedTemplate.icon || "🐝"} {selectedTemplate.name}
              </span>
            </div>
          ) : null}

          <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
            <div className="flex items-center gap-2">
              <label className="qs-label">Bee name</label>
              <InfoHint
                title="Bee name"
                description="Human-readable agent name shown in lists, details, and logs."
                options={["Required field", "Use purpose-based naming", "You can rename it later in agent detail"]}
              />
            </div>
            <input
              value={config.name}
              onChange={(event) => setConfig((prev) => ({ ...prev, name: event.target.value }))}
              className="mt-2 w-full rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-pollen/40"
            />
          </section>

          <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
            <div className="flex items-center gap-2">
              <label className="qs-label">Manager / Swarm</label>
              <InfoHint
                title="Manager / Swarm"
                description="Defines which colony the agent belongs to. Unassigned agents work independently."
                options={["Inherited context from swarm", "Better domain organization", "Can remain unassigned"]}
              />
            </div>
            <p className="mt-1 font-(family-name:--font-poppins) text-xs text-zinc-600">
              Anchor this bee under a colony, or leave unassigned.
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <button
                type="button"
                onClick={() => setConfig((prev) => ({ ...prev, swarm_id: "" }))}
                className={cn(
                  "flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition",
                  !config.swarm_id
                    ? "border-pollen/40 bg-pollen/10 text-pollen"
                    : "border-(--qs-border) bg-black/25 text-(--qs-text-3) hover:border-(--qs-border-2) hover:text-(--qs-text-2)",
                )}
              >
                <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-zinc-600" aria-hidden />
                <span>No manager — unassigned</span>
              </button>

              {swarms
                .filter((swarm) => swarm.is_active !== false && !String(swarm.name).includes("__inactive_"))
                .map((swarm) => {
                  const accent = swarmAccentHex(swarm);
                  const selected = config.swarm_id === swarm.id;
                  return (
                    <button
                      key={swarm.id}
                      type="button"
                      onClick={() => setConfig((prev) => ({ ...prev, swarm_id: swarm.id }))}
                      className={cn(
                        "flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition",
                        selected
                          ? "bg-black/55"
                          : "border-(--qs-border) bg-black/25 text-(--qs-text-3) hover:border-(--qs-border-2) hover:text-(--qs-text-2)",
                      )}
                      style={
                        selected
                          ? {
                              borderColor: `${accent}77`,
                              backgroundColor: `${accent}14`,
                              color: accent,
                            }
                          : undefined
                      }
                    >
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full shadow-[0_0_10px_rgb(255_184_0/0.35)]"
                        style={{ backgroundColor: accent }}
                        aria-hidden
                      />
                      <div className="min-w-0 flex-1">
                        <div className={cn("font-semibold text-[#fafafa]", selected && "text-inherit")}>{swarm.name}</div>
                        <div className="text-[11px] text-zinc-500">
                          {swarmDisplayRole(swarm)} · {swarm.member_count ?? 0} bees
                        </div>
                      </div>
                      {selected ? <span className="font-mono text-xs">✓</span> : null}
                    </button>
                  );
                })}

              {swarms.filter((swarm) => swarm.is_active !== false && !String(swarm.name).includes("__inactive_")).length === 0 ? (
                <div className="rounded-xl px-3 py-2 font-(family-name:--font-poppins) text-xs text-zinc-500">
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
            <div className="flex items-center gap-2">
              <label className="qs-label">System prompt</label>
              <InfoHint
                title="System prompt"
                description="Defines the persistent behavior and role of the agent. This is its core instruction."
                options={["Persona and constraints", "Output style and depth", "Safety and no-go rules"]}
              />
            </div>
            <textarea
              rows={5}
              value={config.system_prompt}
              onChange={(event) => setConfig((prev) => ({ ...prev, system_prompt: event.target.value }))}
              className="mt-2 w-full resize-y rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-cyan/30"
            />
            <div className="mt-4 flex items-center gap-2">
              <label className="qs-label">Task template</label>
              <InfoHint
                title="Task template"
                description="Pre-filled user prompt for recurring tasks. Speeds up daily workflows."
                options={["Reusable instructions", "Structured sections", "Can stay empty for ad-hoc runs"]}
              />
            </div>
            <textarea
              rows={3}
              value={config.user_prompt}
              onChange={(event) => setConfig((prev) => ({ ...prev, user_prompt: event.target.value }))}
              className="mt-2 w-full resize-y rounded-xl border border-white/15 bg-black/50 px-3 py-2.5 text-sm text-[#fafafa] outline-none focus:border-cyan/30"
            />
          </section>

          <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
            <div className="flex items-center gap-2">
              <p className="qs-label">Tools</p>
              <InfoHint
                title="Tools"
                description="Allowed agent capabilities. Each enabled tool expands what the agent can do."
                options={["Web + data feeds", "Keep minimal set for reliability", "Disable tools not needed"]}
              />
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              {ALL_TOOLS.map((tool) => {
                const enabled = config.tools.includes(tool.id);
                return (
                  <button
                    key={tool.id}
                    type="button"
                    onClick={() =>
                      setConfig((prev) => ({
                        ...prev,
                        tools: enabled ? prev.tools.filter((id) => id !== tool.id) : [...prev.tools, tool.id],
                      }))
                    }
                    className={configureOptionClass(enabled, "pollen", "xs")}
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
              <div className="flex items-center gap-2">
                <p className="qs-label">Output</p>
                <InfoHint
                  title="Output format"
                  description="Defines the result format returned by the agent."
                  options={["Text/Markdown for humans", "JSON/CSV for pipelines", "Excel for reporting"]}
                />
              </div>
              <div className="mt-3 flex flex-col gap-2">
                {OUTPUT_FORMATS.map((format) => (
                  <button
                    key={format.id}
                    type="button"
                    onClick={() => setConfig((prev) => ({ ...prev, output_format: format.id }))}
                    className={configureOptionClass(config.output_format === format.id, "success")}
                  >
                    {format.label}
                  </button>
                ))}
              </div>
            </section>
            <section className="rounded-3xl qs-rim bg-[#0f0f16]/95 p-5">
              <div className="flex items-center gap-2">
                <p className="qs-label">Schedule</p>
                <InfoHint
                  title="Schedule"
                  description="Sets automatic execution interval. Empty value means on-demand mode."
                  options={["On demand", "Hourly intervals", "Daily fixed time"]}
                />
              </div>
              <div className="mt-3 flex flex-col gap-2">
                {SCHEDULE_PRESETS.map((schedule) => (
                  <button
                    key={schedule.label}
                    type="button"
                    onClick={() => setConfig((prev) => ({ ...prev, schedule_value: schedule.value }))}
                    className={configureOptionClass(config.schedule_value === schedule.value, "cyan")}
                  >
                    {schedule.label}
                  </button>
                ))}
              </div>
            </section>
          </div>

          <button
            type="button"
            disabled={saving || !config.name.trim()}
            onClick={() => void saveAgent()}
            className="w-full rounded-xl border-2 border-pollen bg-pollen py-4 font-(family-name:--font-poppins) text-sm font-bold text-black shadow-[0_0_32px_rgb(255_184_0/0.35)] disabled:opacity-45"
          >
            {saving ? "Spawning…" : "Spawn agent"}
          </button>
          <div className="flex justify-center">
            <InfoHint
              title="Spawn agent action"
              description="Creates the agent configuration and redirects to the new agent detail page."
              options={["Validates required fields", "Stores dynamic config", "Keeps selected swarm binding"]}
            />
          </div>
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
