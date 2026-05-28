"use client";

import Link from "next/link";
import { Globe, Mic, Monitor, Plug, Sparkles } from "lucide-react";
import type { JSX } from "react";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { integrationsHubSectionHref } from "@/lib/integrations-hub-routes";
import { integrationsTabHref, type IntegrationsTab } from "@/lib/integrations-routes";

interface IntegrationsEcosystemLaneProps {
  onSelectTab: (tab: IntegrationsTab) => void;
}

const LANES = [
  {
    title: "Connector hub",
    description: "OAuth rail, vault sync, connection tests.",
    href: integrationsHubSectionHref("tools"),
    tab: "hub" as const,
    icon: Plug,
  },
  {
    title: "Tools marketplace",
    description: "One-click install curated API templates.",
    href: integrationsTabHref("marketplace"),
    tab: "marketplace" as const,
    icon: Globe,
  },
  {
    title: "Browser harness",
    description: "Supervised browser sessions with guardrails.",
    href: "/agents#sessions",
    tab: null,
    icon: Monitor,
  },
  {
    title: "Ballroom voice",
    description: "Multimodal swarm collaboration lane.",
    href: "/ballroom",
    tab: null,
    icon: Mic,
  },
];

/** Cross-linked ecosystem orchestration shortcuts on the integrations overview. */
export function IntegrationsEcosystemLane({ onSelectTab }: IntegrationsEcosystemLaneProps): JSX.Element {
  return (
    <V4Card id="ecosystem" className="scroll-mt-28">
      <V4CardHeader
        kicker="Phase 12 · Ecosystem"
        title="Ecosystem Orchestration"
        description="Install tools, supervise browser agents, and run voice-driven swarm loops from one operator surface."
        actions={
          <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
            <Sparkles className="h-3.5 w-3.5" aria-hidden />
            Supervisor lane
          </Link>
        }
      />
      <div className="v4-cols-2 lg:grid-cols-4">
        {LANES.map((lane) => {
          const Icon = lane.icon;
          if (lane.tab) {
            return (
              <button
                key={lane.title}
                type="button"
                className="v4-int-card text-left transition hover:border-pollen/40"
                onClick={() => onSelectTab(lane.tab!)}
              >
                <div className="v4-int-logo mb-3">
                  <Icon className="h-[18px] w-[18px]" aria-hidden />
                </div>
                <p className="v4-int-name">{lane.title}</p>
                <p className="v4-int-meta">{lane.description}</p>
              </button>
            );
          }
          return (
            <Link
              key={lane.title}
              href={lane.href}
              className="v4-int-card block transition hover:border-pollen/40"
            >
              <div className="v4-int-logo mb-3">
                <Icon className="h-[18px] w-[18px]" aria-hidden />
              </div>
              <p className="v4-int-name">{lane.title}</p>
              <p className="v4-int-meta">{lane.description}</p>
            </Link>
          );
        })}
      </div>
    </V4Card>
  );
}
