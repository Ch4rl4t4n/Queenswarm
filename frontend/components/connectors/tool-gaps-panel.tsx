"use client";

import Link from "next/link";
import { AlertTriangle, Loader2, PlugIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface ToolGapRow {
  kind: string;
  connector_slug: string;
  tool_name: string;
  message: string;
  occurrences: number;
  suggested_template_id?: string | null;
  integrations_href?: string | null;
}

interface ToolGapsPayload {
  enabled: boolean;
  generated_at: string;
  gaps: ToolGapRow[];
}

interface ToolGapsPanelProps {
  /** When set, renders as embedded block without outer V4Card. */
  embedded?: boolean;
  className?: string;
  onInstalled?: () => void;
}

export function ToolGapsPanel({ embedded = false, className, onInstalled }: ToolGapsPanelProps) {
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [gaps, setGaps] = useState<ToolGapRow[]>([]);

  const load = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const payload = await hiveGet<ToolGapsPayload>("tools/tool-gaps");
      setGaps(Array.isArray(payload.gaps) ? payload.gaps : []);
    } catch {
      setGaps([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const installTemplate = async (templateId: string): Promise<void> => {
    setBusyId(templateId);
    try {
      await hivePostJson("tools/marketplace/install", {
        source: "phase3_template",
        entry_id: templateId,
      });
      toast.success("Connector installed — add credentials in Integrations.");
      await load();
      onInstalled?.();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Install failed.");
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return null;
  }

  if (gaps.length === 0) {
    return null;
  }

  const body = (
    <div className="space-y-2">
      {gaps.map((row) => (
        <div
          key={`${row.kind}-${row.connector_slug}-${row.tool_name}`}
          className="rounded-lg border border-magenta/25 bg-magenta/5 px-3 py-2 text-xs"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 font-medium text-(--qs-text)">
              <AlertTriangle className="size-3.5 text-magenta" aria-hidden />
              {row.connector_slug} · {row.tool_name}
            </span>
            <span className="text-(--qs-text-3)">
              {row.kind.replaceAll("_", " ")} · ×{row.occurrences}
            </span>
          </div>
          <p className="mt-1 text-(--qs-text-3)">{row.message}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {row.suggested_template_id ? (
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                disabled={busyId === row.suggested_template_id}
                onClick={() => void installTemplate(row.suggested_template_id!)}
              >
                {busyId === row.suggested_template_id ? (
                  <Loader2 className="size-3.5 animate-spin" aria-hidden />
                ) : (
                  <PlugIcon className="size-3.5" aria-hidden />
                )}
                Install {row.suggested_template_id}
              </button>
            ) : null}
            {row.integrations_href ? (
              <Link href={row.integrations_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                Open Integrations
              </Link>
            ) : null}
            <Link href="/apps-tools/mcp-ops-studio?section=health#mcp-health" className="qs-btn qs-btn--ghost qs-btn--sm">
              MCP Ops Studio
            </Link>
          </div>
        </div>
      ))}
    </div>
  );

  if (embedded) {
    return <div className={cn("space-y-2", className)}>{body}</div>;
  }

  return (
    <V4Card className={cn("border-magenta/30", className)}>
      <V4CardHeader
        title="Actionable tool gaps"
        description="Agent sessions failed on missing MCP connectors — install templates below or in marketplace."
      />
      {body}
    </V4Card>
  );
}
