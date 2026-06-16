"use client";

import { useEffect, useState } from "react";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

export type AppsToolsPolicyModuleKey =
  | "marketing_automation"
  | "ecommerce_workspace"
  | "mcp_ops_studio"
  | "trading_automation"
  | "browser_automation"
  | "content_factory"
  | "research_workspace"
  | "analytics_workspace"
  | "trading_journal"
  | "live_lane";

interface ModulePolicyPack {
  module_key: AppsToolsPolicyModuleKey;
  enabled: boolean;
  risk_tier: "read" | "write" | "publish" | "financial";
  requires_approval: boolean;
  cooldown_sec: number | null;
  rate_limit_max_global: number | null;
  rate_limit_window_sec: number | null;
}

interface ModulePolicyPackPillProps {
  moduleKey: AppsToolsPolicyModuleKey;
}

function compactPolicyLabel(pack: ModulePolicyPack): string {
  const chunks: string[] = [];
  chunks.push(pack.requires_approval ? "approval" : "auto");
  if (pack.cooldown_sec && pack.cooldown_sec > 0) {
    chunks.push(`${pack.cooldown_sec}s cooldown`);
  }
  if (pack.rate_limit_max_global && pack.rate_limit_window_sec) {
    const windowHours = Math.max(1, Math.round(pack.rate_limit_window_sec / 3600));
    chunks.push(`${pack.rate_limit_max_global}/${windowHours}h`);
  }
  return chunks.join(" · ");
}

export function ModulePolicyPackPill({ moduleKey }: ModulePolicyPackPillProps) {
  const [pack, setPack] = useState<ModulePolicyPack | null>(null);

  useEffect(() => {
    let active = true;
    const load = async (): Promise<void> => {
      try {
        const data = await hiveGet<ModulePolicyPack>(`operator/module-policy-packs/${moduleKey}`);
        if (!active) return;
        setPack(data);
      } catch (exc) {
        if (exc instanceof HiveApiError && exc.status === 404) {
          return;
        }
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [moduleKey]);

  if (!pack) {
    return null;
  }

  const tone = pack.requires_approval ? "warn" : "ok";
  return <V4Badge tone={tone}>Policy: {compactPolicyLabel(pack)}</V4Badge>;
}
