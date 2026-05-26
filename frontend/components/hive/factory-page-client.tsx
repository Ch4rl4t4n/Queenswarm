"use client";

import Link from "next/link";
import { Factory, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { ExecutionStudioMicroSaasFactoryPanel } from "@/components/connectors/execution-studio-micro-saas-factory-panel";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { V4Card, V4PageCanvas } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface MicroSaasBlueprint {
  enabled: boolean;
  phases: Array<{ id: string; label: string; detail: string }>;
  stack: Record<string, string>;
  disclaimer: string;
}

export function FactoryPageClient(): JSX.Element {
  const [blueprint, setBlueprint] = useState<MicroSaasBlueprint | null>(null);
  const [loading, setLoading] = useState(true);
  const [panelErr, setPanelErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<MicroSaasBlueprint>("marketing/micro-saas-blueprint");
      setBlueprint(data);
    } catch {
      setBlueprint(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <V4PageCanvas>
      <HivePageHeader
        className="mb-3 lg:mb-6"
        title="Micro-SaaS Factory"
        subtitle="Scope → landing → auth → Stripe → deploy. Simulate-first mini aplikácie pre solo operátora."
        status={
          <Link href="/swarms/new?template=micro-saas-factory" className="qs-btn qs-btn--primary qs-btn--sm gap-2">
            <Factory className="size-4" aria-hidden />
            Spawn factory swarm
          </Link>
        }
      />

      <ExecutionStudioMicroSaasFactoryPanel onError={setPanelErr} />

      {panelErr ? <p className="mt-3 text-sm text-[#FF3366]">{panelErr}</p> : null}

      <V4Card className="mt-6">
        <h2 className="font-heading text-sm font-semibold text-(--qs-text)">Blueprint fázy</h2>
        {loading ? (
          <p className="mt-3 flex items-center gap-2 text-sm text-(--qs-muted)">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Loading blueprint…
          </p>
        ) : !blueprint?.enabled ? (
          <p className="mt-3 text-sm text-(--qs-text-3)">
            Factory nie je zapnuté — nastav <code className="font-mono text-cyan">MICRO_SAAS_FACTORY_ENABLED=true</code> a
            redeploy.
          </p>
        ) : (
          <>
            <ol className="mt-4 space-y-2">
              {blueprint.phases.map((phase, index) => (
                <li
                  key={phase.id}
                  className="rounded-lg border border-(--qs-border)/60 bg-black/20 px-3 py-2 text-sm"
                >
                  <span className="font-mono text-xs text-pollen">0{index + 1}</span>
                  <p className="mt-1 font-medium text-(--qs-text)">{phase.label}</p>
                  <p className="mt-0.5 text-xs text-(--qs-muted)">{phase.detail}</p>
                </li>
              ))}
            </ol>
            <dl className="mt-4 grid gap-2 sm:grid-cols-2">
              {Object.entries(blueprint.stack).map(([key, value]) => (
                <div key={key} className="rounded-lg border border-(--qs-border)/60 bg-black/20 p-3">
                  <dt className="text-[10px] uppercase text-(--qs-text-3)">{key}</dt>
                  <dd className="mt-1 text-sm text-cyan">{value}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-4 text-xs text-(--qs-text-3)">{blueprint.disclaimer}</p>
          </>
        )}
      </V4Card>

      <div className="mt-4 flex flex-wrap gap-3 text-sm">
        <Link href="/integrations?tab=studio#micro-saas-factory" className="text-cyan hover:underline">
          Execution Studio checklist
        </Link>
        <Link href="/agents?preset=marketing-draft" className="text-cyan hover:underline">
          Marketing draft session
        </Link>
      </div>
    </V4PageCanvas>
  );
}
