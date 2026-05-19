"use client";

import Link from "next/link";
import { Mic } from "lucide-react";

import { V4Badge } from "@/components/ui/v4/v4-badge";
import { V4Card } from "@/components/ui/v4/v4-card";
import type { AgentRow } from "@/lib/hive-types";

interface V4BallroomParticipantsProps {
  agents: AgentRow[];
}

function participantGlyph(agent: AgentRow): string {
  const n = agent.name.toLowerCase();
  if (n.includes("orchestr") || (agent.hive_tier ?? "").toLowerCase() === "orchestrator") return "👑";
  if (n.includes("scribe")) return "📜";
  if (n.includes("sentinel")) return "🛡";
  if (n.includes("forge")) return "⚒";
  if (n.includes("oracle")) return "🔮";
  return "🐝";
}

function isLive(agent: AgentRow): boolean {
  const u = String(agent.status).toUpperCase();
  return u === "RUNNING" || u === "BUSY" || u === "ACTIVE";
}

/** Compact Ballroom presence strip — below Queen mission on dashboard. */
export function V4BallroomParticipants({ agents }: V4BallroomParticipantsProps) {
  const roster = agents.slice(0, 6);
  const liveCount = roster.filter(isLive).length;

  return (
    <V4Card tight className="v4-card-interactive">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 flex-wrap items-center gap-4">
          <span className="v4-label-kicker shrink-0">Ballroom · live participants</span>
          <div className="v4-participants">
            {roster.length === 0 ? (
              <span className="text-xs text-(--qs-text-3)">No agents in roster</span>
            ) : (
              roster.map((agent) => (
                <div key={agent.id} className="v4-participant" title={agent.name}>
                  {participantGlyph(agent)}
                  {isLive(agent) ? <span className="v4-participant-live" aria-hidden /> : null}
                </div>
              ))
            )}
          </div>
          <span className="text-xs text-(--qs-text-3)">
            {liveCount}/{Math.max(roster.length, 1)} live · tap Open for full session
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {liveCount > 0 ? <V4Badge tone="ok">LIVE</V4Badge> : null}
          <Link href="/ballroom" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
            <Mic className="h-4 w-4" aria-hidden />
            Open Ballroom
          </Link>
        </div>
      </div>
    </V4Card>
  );
}
