"use client";

import { PauseIcon, PlayIcon } from "lucide-react";
import { toast } from "sonner";

import { NeonButton } from "@/components/ui/neon-button";
import { hivePostJson } from "@/lib/api";

interface AgentRemoteControlsProps {
  agentId: string;
}

/** Pause / resume controls hitting `/agents/{id}/pause|resume`. */
export function AgentRemoteControls({ agentId }: AgentRemoteControlsProps) {
  async function pause(): Promise<void> {
    try {
      await hivePostJson(`agents/${agentId}/pause`, {});
      toast.success("Bee paused");
    } catch (exc) {
      toast.error(exc instanceof Error ? exc.message : "Pause failed");
    }
  }

  async function resume(): Promise<void> {
    try {
      await hivePostJson(`agents/${agentId}/resume`, {});
      toast.success("Bee resumed");
    } catch (exc) {
      toast.error(exc instanceof Error ? exc.message : "Resume failed");
    }
  }

  return (
    <div className="flex flex-wrap gap-3">
      <NeonButton type="button" variant="ghost" className="gap-2" onClick={() => void pause()}>
        <PauseIcon className="h-4 w-4" /> Pause
      </NeonButton>
      <NeonButton type="button" variant="primary" className="gap-2 text-black" onClick={() => void resume()}>
        <PlayIcon className="h-4 w-4" /> Resume
      </NeonButton>
    </div>
  );
}
