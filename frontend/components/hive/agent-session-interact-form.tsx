"use client";

import type { JSX } from "react";

import { useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hivePostJson } from "@/lib/api";
import type { SupervisorSessionEventRow } from "@/lib/hive-types";

interface AgentSessionInteractFormProps {
  sessionId: string;
  onInteractionAppended: (event: SupervisorSessionEventRow) => void;
}

export function AgentSessionInteractForm({
  sessionId,
  onInteractionAppended,
}: AgentSessionInteractFormProps): JSX.Element {
  const [command, setCommand] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitInteraction(): Promise<void> {
    const value = command.trim();
    if (!value) return;
    setBusy(true);
    try {
      const event = await hivePostJson<SupervisorSessionEventRow>(`agents/sessions/${sessionId}/interact`, {
        command: value,
      });
      setCommand("");
      onInteractionAppended(event);
      toast.success("Interaction sent.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Interaction failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
        Session command
      </label>
      <textarea
        className="qs-input min-h-20 w-full"
        value={command}
        onChange={(event) => setCommand(event.target.value)}
        placeholder="Ask sub-agents for a refinement, critique, or next step."
      />
      <div className="flex justify-end">
        <button
          type="button"
          disabled={busy || command.trim().length < 1}
          className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40"
          onClick={() => void submitInteraction()}
        >
          {busy ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}

