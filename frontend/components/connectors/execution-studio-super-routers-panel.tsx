"use client";

import dynamic from "next/dynamic";
import { memo, useState } from "react";

const SuperToolRouterPanel = dynamic(
  () => import("@/components/connectors/super-tool-router-panel").then((mod) => ({ default: mod.SuperToolRouterPanel })),
  { ssr: false, loading: () => <div className="min-h-[8rem] animate-pulse rounded-lg bg-white/5" aria-hidden /> },
);

export interface SuperRouterItem {
  slug: string;
  name: string;
  is_active: boolean;
  routing_mode: string;
  manager_slugs: string[];
  connector_slugs: string[];
}

export interface SuperRouterSnapshot {
  count: number;
  active_count: number;
  items: SuperRouterItem[];
}

export interface ExecutionStudioSuperRoutersPanelProps {
  superRouters: SuperRouterSnapshot | undefined;
}

function ExecutionStudioSuperRoutersPanelInner({ superRouters }: ExecutionStudioSuperRoutersPanelProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  return (
    <div className="qs-bubble qs-bubble--tint-cyan shrink-0 space-y-3 p-4">
      <p className="text-sm font-semibold text-(--qs-text)">
        Super Tool Routers ({superRouters?.active_count ?? 0}/{superRouters?.count ?? 0} active)
      </p>
      <p className="text-xs text-(--qs-text-3)">
        Priority = fallback chain · Research→action = verify data before writes · Parallel = invoke all connectors.
      </p>
      {(superRouters?.items.length ?? 0) > 0 ? (
        <ul className="space-y-2">
          {superRouters?.items.map((router) => (
            <li key={router.slug} className="qs-bubble-inner px-3 py-2 text-xs">
              <span className="font-semibold text-(--qs-text)">{router.name}</span>
              <span className="ml-2 font-mono text-[10px] text-pollen">{router.routing_mode}</span>
              <p className="mt-1 text-[10px] text-(--qs-text-4)">{router.connector_slugs.join(" → ")}</p>
            </li>
          ))}
        </ul>
      ) : null}
      <details
        className="qs-bubble-inner p-3"
        open={detailsOpen}
        onToggle={(event) => setDetailsOpen(event.currentTarget.open)}
      >
        <summary className="cursor-pointer text-xs font-semibold text-(--qs-text-2)">
          Manage routers (create / presets / toggle)
        </summary>
        <div className="mt-3 max-h-[28rem] overflow-y-auto hive-scrollbar">
          {detailsOpen ? <SuperToolRouterPanel /> : null}
        </div>
      </details>
    </div>
  );
}

export const ExecutionStudioSuperRoutersPanel = memo(ExecutionStudioSuperRoutersPanelInner);
