"use client";

import { PauseIcon, PlayIcon } from "lucide-react";
import { toast } from "sonner";

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
      <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-2" onClick={() => void pause()}>
        <PauseIcon className="h-4 w-4" aria-hidden />
        Pause
      </button>
      <button type="button" className="qs-btn qs-btn--primary qs-btn--sm inline-flex items-center gap-2" onClick={() => void resume()}>
        <PlayIcon className="h-4 w-4" aria-hidden />
        Resume
      </button>
    </div>
  );
}
