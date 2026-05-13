"use client";

import { HexAgentCard } from "@/components/hive/hex-agent-card";
import type { AgentRow } from "@/lib/hive-types";

interface AgentHexCardProps {
  agent: AgentRow;
}

export function AgentHexCard({ agent }: AgentHexCardProps): JSX.Element {
  const target = agent.has_universal_config ? `/agents/${agent.id}` : `/agents/${agent.id}/edit`;
  return (
    <HexAgentCard
      agent={agent}
      href={target}
      showPerformance={false}
      className="group"
    />
  );
}
