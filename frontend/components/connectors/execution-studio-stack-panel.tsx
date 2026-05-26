"use client";

import { CheckCircle2 } from "lucide-react";
import { memo, useCallback, useMemo, useState } from "react";

import { ExecutionStackGrid } from "@/components/connectors/execution-stack-grid";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { ExecutionMode, SetupStep, StudioConnection } from "@/lib/execution-studio-shared-types";

type RiskTier = "read" | "write" | "publish" | "financial";

interface StudioPackTemplate {
  template_id: string;
  slug: string;
  display_name: string;
  installed: boolean;
}

interface StudioPack {
  id: string;
  label: string;
  description: string;
  templates: StudioPackTemplate[];
}

export interface ExecutionStudioStackPanelProps {
  connections: StudioConnection[];
  packs: StudioPack[];
  setupSteps: SetupStep[];
  defaultMode: ExecutionMode;
  loading: boolean;
  executeResult: string | null;
  onError: (message: string | null) => void;
  onExecuteResult: (message: string | null) => void;
  onReloadOverview: () => Promise<void>;
}

function ExecutionStudioStackPanelInner({
  connections,
  packs,
  setupSteps,
  defaultMode,
  loading,
  executeResult,
  onError,
  onExecuteResult,
  onReloadOverview,
}: ExecutionStudioStackPanelProps) {
  const [testBusyId, setTestBusyId] = useState<string | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [guide, setGuide] = useState<Record<string, unknown> | null>(null);

  const testConnection = useCallback(
    async (connection: StudioConnection) => {
      setTestBusyId(connection.id);
      onError(null);
      try {
        await hivePostJson(`connectors/dynamic/${encodeURIComponent(connection.id)}/test`, {});
        await onReloadOverview();
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Connection test failed.");
      } finally {
        setTestBusyId(null);
      }
    },
    [onError, onReloadOverview],
  );

  const openGuide = useCallback(async (slug: string) => {
    setSelectedSlug(slug);
    setGuide(null);
    try {
      const data = await hiveGet<Record<string, unknown>>(`execution-studio/guides/${encodeURIComponent(slug)}`);
      setGuide(data);
    } catch {
      setGuide(null);
    }
  }, []);

  const dryRunFirstTool = useCallback(
    async (connection: StudioConnection) => {
      onExecuteResult(null);
      onError(null);
      try {
        const registry = await hiveGet<{ items: Array<{ slug: string; tools: Array<{ name: string }> }> }>(
          "tools/registry",
        );
        const row = registry.items.find((item) => item.slug === connection.slug);
        const toolName = row?.tools?.[0]?.name;
        if (!toolName) {
          onExecuteResult("No manifest tools found for dry-run.");
          return;
        }
        const out = await hivePostJson<{
          ok: boolean;
          mode: ExecutionMode;
          message?: string;
          error?: string;
          risk_tier?: RiskTier;
        }>("execution-studio/execute", {
          connector_slug: connection.slug,
          tool_name: toolName,
          arguments: {},
          mode: defaultMode,
        });
        onExecuteResult(out.message ?? out.error ?? (out.ok ? "Dry-run OK" : "Dry-run failed"));
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Dry-run failed.");
      }
    },
    [defaultMode, onError, onExecuteResult],
  );

  const selectedConnection = useMemo(
    () => connections.find((row) => row.slug === selectedSlug) ?? null,
    [connections, selectedSlug],
  );

  return (
    <>
      <div className="flex shrink-0 items-center justify-between gap-2">
        <p className="v4-field-label">Your execution stack ({connections.length})</p>
      </div>

      <ExecutionStackGrid
        connections={connections}
        loading={loading}
        testBusyId={testBusyId}
        onOpenGuide={(slug) => void openGuide(slug)}
        onTest={(connection) => {
          const full = connections.find((row) => row.id === connection.id);
          if (full) void testConnection(full);
        }}
        onDryRun={(connection) => {
          const full = connections.find((row) => row.id === connection.id);
          if (full) void dryRunFirstTool(full);
        }}
      />

      <div className="space-y-3">
        {packs.length ? (
          <div className="space-y-3">
            <p className="v4-field-label">Connection packs</p>
            <div className="grid gap-3 md:grid-cols-2">
              {packs.map((pack) => (
                <article key={pack.id} className="v4-dream-cycle-card p-3">
                  <p className="text-sm font-semibold text-(--qs-text)">{pack.label}</p>
                  <p className="mt-1 text-xs text-(--qs-text-3)">{pack.description}</p>
                  <p className="mt-2 font-mono text-[10px] text-(--qs-text-4)">
                    {pack.templates.filter((t) => t.installed).length}/{pack.templates.length} installed
                  </p>
                </article>
              ))}
            </div>
          </div>
        ) : null}

        {selectedConnection && guide ? (
          <div className="v4-dream-cycle-card p-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-(--qs-text)">
              <CheckCircle2 className="h-4 w-4 text-pollen" aria-hidden />
              Setup guide — {selectedConnection.display_name}
            </p>
            <ol className="mt-3 space-y-2">
              {setupSteps.map((step, index) => (
                <li key={step.id} className="flex gap-3 text-xs text-(--qs-text-2)">
                  <span className="font-mono text-pollen">{index + 1}.</span>
                  <span>
                    <span className="font-semibold text-(--qs-text)">{step.title}</span>
                    <span className="mt-0.5 block text-(--qs-text-3)">{step.detail}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        ) : null}

        {executeResult ? (
          <p className="rounded-xl border border-(--qs-green)/30 bg-(--qs-green)/10 px-3 py-2 text-xs text-(--qs-green)">
            {executeResult}
          </p>
        ) : null}
      </div>
    </>
  );
}

export const ExecutionStudioStackPanel = memo(ExecutionStudioStackPanelInner);
