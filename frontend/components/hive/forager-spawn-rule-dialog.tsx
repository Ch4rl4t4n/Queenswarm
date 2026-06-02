"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HiveModalShell } from "@/components/hive/hive-modal-shell";
import { QsSelect } from "@/components/ui/qs-select";
import { HiveApiError, hivePutJson } from "@/lib/api";
import type { ForagerRow, ForagersOverviewConfiguration } from "@/lib/hive-types";

interface AgentTemplateLite {
  id: string;
  name: string;
  category: string;
}

interface ForagerSpawnRuleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  foragers: ForagerRow[];
  configurations: ForagersOverviewConfiguration[];
  templates: AgentTemplateLite[];
  canManage: boolean;
  onSaved: () => void;
}

const COOLDOWN_OPTIONS = [
  { value: "1h", label: "1 hour" },
  { value: "4h", label: "4 hours" },
  { value: "24h", label: "24 hours" },
] as const;

export function ForagerSpawnRuleDialog({
  open,
  onOpenChange,
  foragers,
  configurations,
  templates,
  canManage,
  onSaved,
}: ForagerSpawnRuleDialogProps): JSX.Element {
  const [foragerId, setForagerId] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [minItems, setMinItems] = useState(5);
  const [cooldown, setCooldown] = useState("1h");
  const [busy, setBusy] = useState(false);

  const foragerOptions = useMemo(
    () =>
      configurations.map((row) => ({
        value: row.id,
        label: row.source_name,
      })),
    [configurations],
  );

  const templateOptions = useMemo(
    () =>
      templates.map((row) => ({
        value: row.id,
        label: row.name,
      })),
    [templates],
  );

  useEffect(() => {
    if (!open) return;
    const first = configurations[0]?.id ?? "";
    setForagerId(first);
    setTemplateId(templates[0]?.id ?? "");
    setMinItems(5);
    setCooldown("1h");
  }, [open, configurations, templates]);

  async function handleSave(): Promise<void> {
    if (!canManage || !foragerId || !templateId) {
      toast.error("Select a forager and agent template.");
      return;
    }
    const forager = foragers.find((row) => row.id === foragerId);
    const template = templates.find((row) => row.id === templateId);
    if (!forager || !template) {
      toast.error("Forager or template not found.");
      return;
    }
    const configRow = configurations.find((row) => row.id === foragerId);
    const displayName = configRow?.source_name ?? forager.name;
    const ruleId = crypto.randomUUID();
    const whenLabel = `${displayName} finds ≥${minItems} matching items`;
    const spawnLabel = `${template.name} → swarm`;

    setBusy(true);
    try {
      const filterCfg = { ...(forager.filter_config || {}) };
      const rules = Array.isArray(filterCfg.auto_spawn_rules) ? [...filterCfg.auto_spawn_rules] : [];
      rules.push({
        id: ruleId,
        when_label: whenLabel,
        spawn_label: spawnLabel,
        min_items: minItems,
        cooldown,
        enabled: true,
        agent_template_id: templateId,
      });
      filterCfg.auto_spawn_rules = rules;
      if (!forager.agent_template_id) {
        await hivePutJson(`foragers/${encodeURIComponent(foragerId)}`, {
          filter_config: filterCfg,
          agent_template_id: templateId,
        });
      } else {
        await hivePutJson(`foragers/${encodeURIComponent(foragerId)}`, {
          filter_config: filterCfg,
        });
      }
      toast.success("Auto-spawn rule saved");
      onOpenChange(false);
      onSaved();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Could not save spawn rule");
    } finally {
      setBusy(false);
    }
  }

  return (
    <HiveModalShell
      open={open}
      onClose={() => onOpenChange(false)}
      labelledBy="forager-spawn-rule-title"
      panelClassName="max-w-lg w-full"
    >
      <h2 id="forager-spawn-rule-title" className="text-lg font-semibold text-(--qs-text-1)">
        Add auto-spawn rule
      </h2>
      <p className="mt-1 text-sm text-(--qs-text-3)">
        When a forager harvests enough items, spawn a scout from the linked template.
      </p>
      <div className="mt-4 flex flex-col gap-3">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="text-(--qs-text-2)">Forager</span>
          <QsSelect value={foragerId} onValueChange={setForagerId} options={foragerOptions} disabled={!canManage || busy} />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="text-(--qs-text-2)">Agent template</span>
          <QsSelect
            value={templateId}
            onValueChange={setTemplateId}
            options={templateOptions}
            disabled={!canManage || busy || !templateOptions.length}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="text-(--qs-text-2)">Minimum items threshold</span>
          <input
            type="number"
            min={1}
            max={9999}
            value={minItems}
            onChange={(e) => setMinItems(Math.max(1, Number(e.target.value) || 1))}
            className="qs-input h-10 rounded-(--qs-radius-sm)"
            disabled={!canManage || busy}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="text-(--qs-text-2)">Cooldown</span>
          <QsSelect
            value={cooldown}
            onValueChange={setCooldown}
            options={COOLDOWN_OPTIONS.map((row) => ({ value: row.value, label: row.label }))}
            disabled={!canManage || busy}
          />
        </label>
      </div>
      <div className="mt-6 flex justify-end gap-2">
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" disabled={busy} onClick={() => onOpenChange(false)}>
          Cancel
        </button>
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm"
          disabled={!canManage || busy || !foragerId || !templateId}
          onClick={() => void handleSave()}
        >
          Save rule
        </button>
      </div>
    </HiveModalShell>
  );
}
