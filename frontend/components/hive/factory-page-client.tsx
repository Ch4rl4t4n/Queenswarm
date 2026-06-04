"use client";

import Link from "next/link";
import { Factory, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { ExecutionStudioMicroSaasFactoryPanel } from "@/components/connectors/execution-studio-micro-saas-factory-panel";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { V4Card } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import {
  contentFactoryPackFactoryHref,
  FACTORY_CROSS_LINK_LABELS,
} from "@/lib/factory-content-factory-routes";

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
    <HivePageShell
      title="Micro-SaaS Factory"
      subtitle="Scope → landing → auth → monetization lane → deploy. Simulate-first mini apps for solo operators."
      hintKey="factory"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href={contentFactoryPackFactoryHref()} className="qs-btn qs-btn--ghost qs-btn--sm">
            {FACTORY_CROSS_LINK_LABELS.toContentFactoryModule}
          </Link>
          <Link href="/swarms/new?template=micro-saas-factory" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
            <Factory className="size-4" aria-hidden />
            Open factory template
          </Link>
        </div>
      }
      error={panelErr ? { message: panelErr, onDismiss: () => setPanelErr(null) } : null}
    >
      <ExecutionStudioMicroSaasFactoryPanel onError={setPanelErr} hideSpawnAction />

      <V4Card>
        <h2 className="font-heading text-sm font-semibold text-(--qs-text)">Blueprint phases</h2>
        {loading ? (
          <p className="mt-3 flex items-center gap-2 text-sm text-(--qs-muted)">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Loading blueprint…
          </p>
        ) : !blueprint?.enabled ? (
          <p className="mt-3 text-sm text-(--qs-text-3)">
            Factory is disabled — set <code className="font-mono text-cyan">MICRO_SAAS_FACTORY_ENABLED=true</code> and
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
    </HivePageShell>
  );
}
