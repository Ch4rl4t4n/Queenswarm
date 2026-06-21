"use client";

import Link from "next/link";
import { Loader2, PlugIcon, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type {
  HarnessIntelligenceApplyResponse,
  HarnessIntelligenceScanPayload,
  HarnessSnapshotPayload,
} from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface SelfExtendingMarketplacePanelProps {
  snapshot: HarnessSnapshotPayload;
}

/** Forager Intelligence → one-click MCP preset install (self-extending hive). */
export function SelfExtendingMarketplacePanel({ snapshot }: SelfExtendingMarketplacePanelProps): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const status = snapshot.self_extending_marketplace;
  const [scanBusy, setScanBusy] = useState(false);
  const [applyBusy, setApplyBusy] = useState<string | null>(null);
  const [scan, setScan] = useState<HarnessIntelligenceScanPayload | null>(null);

  const runScan = useCallback(async () => {
    setScanBusy(true);
    try {
      const body = await hivePostJson<HarnessIntelligenceScanPayload>("harness/intelligence-scan", {});
      setScan(body);
      toast.success(`Forager scan: ${body.proposal_count} proposal(s)`);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Intelligence scan failed.");
    } finally {
      setScanBusy(false);
    }
  }, []);

  useEffect(() => {
    if (hasFeature("self_extending_tool_marketplace") && status?.enabled) {
      void runScan();
    }
  }, [hasFeature, runScan, status?.enabled]);

  if (!hasFeature("self_extending_tool_marketplace") || !status?.enabled) {
    return null;
  }

  async function applyProposal(kind: string, target: string): Promise<void> {
    const key = `${kind}:${target}`;
    setApplyBusy(key);
    try {
      const result = await hivePostJson<HarnessIntelligenceApplyResponse>("harness/intelligence-apply", {
        kind,
        target,
      });
      toast.success(
        result.status === "already_installed"
          ? `${result.template_title ?? target} already installed`
          : `Installed ${result.template_title ?? target}`,
      );
      await runScan();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Install failed.");
    } finally {
      setApplyBusy(null);
    }
  }

  const installable = scan?.self_extending?.installable_count ?? 0;
  const proposals = (scan?.proposals ?? []).filter((row) => row.action === "install_marketplace");

  return (
    <V4Card className="border-cyan/25">
      <V4CardHeader
        kicker="Self-extending hive"
        title="Tool marketplace from Forager scan"
        description="Read-only intelligence scan → one-click Phase3 MCP preset install. Verified connector rows only — no raw secrets."
        hint={sectionHintNode("integrationsSelfExtending")}
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <V4Badge tone="ok">Enabled</V4Badge>
        <V4Badge tone={installable > 0 ? "warn" : "info"}>
          {installable} installable
        </V4Badge>
      </div>
      <div className="v4-dream-cycle-card-actions">
        <button
          type="button"
          className={cn("qs-btn qs-btn--ghost qs-btn--sm", scanBusy && "opacity-60")}
          disabled={scanBusy}
          onClick={() => void runScan()}
        >
          {scanBusy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <RefreshCw className="size-4" aria-hidden />}
          Rescan
        </button>
        <Link href="/integrations?tab=hub&hubSection=tools#hub-tools" className="qs-btn qs-btn--ghost qs-btn--sm">
          Open Tool Hub
        </Link>
      </div>

      {proposals.length === 0 ? (
        <p className="mt-4 text-sm text-(--qs-muted)">
          No MCP preset gaps detected — hive tools match Phase3 catalog and skills index.
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {proposals.slice(0, 10).map((item) => {
            const busy = applyBusy === `${item.kind}:${item.target}`;
            return (
              <li
                key={`${item.kind}-${item.target}`}
                className="flex flex-col gap-3 rounded-lg border border-(--qs-border) bg-black/20 p-3 text-sm"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Sparkles className="size-4 text-cyan" aria-hidden />
                    <span className="font-semibold text-(--qs-text)">
                      {item.template_title ?? item.target}
                    </span>
                    {item.installed ? <V4Badge tone="ok">Installed</V4Badge> : <V4Badge tone="warn">Gap</V4Badge>}
                  </div>
                  {item.template_summary ? (
                    <p className="mt-2 text-xs text-(--qs-muted)">{item.template_summary}</p>
                  ) : (
                    <p className="mt-2 text-(--qs-muted)">{item.rationale}</p>
                  )}
                  {item.skill_doc_hint ? (
                    <p className="mt-2 font-mono text-[10px] text-(--qs-muted)">Skill hint: {item.skill_doc_hint}</p>
                  ) : null}
                </div>
                {!item.installed ? (
                  <div className="v4-dream-cycle-card-actions">
                    <button
                      type="button"
                      className="qs-btn qs-btn--primary qs-btn--sm shrink-0 gap-1"
                      disabled={busy}
                      onClick={() => void applyProposal(item.kind, item.target)}
                    >
                      {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <PlugIcon className="size-4" aria-hidden />}
                      Install preset
                    </button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </V4Card>
  );
}
