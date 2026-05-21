"use client";

import { Loader2Icon, MessageSquarePlusIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type { HarnessSnapshotPayload, SlackTrainerFeedbackResponse } from "@/lib/hive-types";

interface SlackHarnessTrainerPanelProps {
  snapshot: HarnessSnapshotPayload;
}

/** Slack + dashboard feedback loop into behavioral INSTRUCTIONS memory (AnswerThis pattern). */
export function SlackHarnessTrainerPanel({ snapshot }: SlackHarnessTrainerPanelProps): JSX.Element {
  const trainer = snapshot.slack_trainer;
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitFeedback(): Promise<void> {
    const text = feedback.trim();
    if (text.length < 4) {
      toast.error("Feedback must be at least 4 characters.");
      return;
    }
    setBusy(true);
    try {
      const res = await hivePostJson<SlackTrainerFeedbackResponse>("harness/slack-trainer/feedback", {
        feedback: text,
        source: "dashboard",
      });
      toast.success(`Saved to instructions.md (v${res.version})`);
      setFeedback("");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Trainer append failed.");
    } finally {
      setBusy(false);
    }
  }

  const ready = trainer?.signing_secret_configured && trainer?.tenant_id_configured;

  return (
    <V4Card>
      <V4CardHeader
        kicker="Slack harness trainer"
        title="Teach Queen via feedback"
        description="Append operator corrections to behavioral memory — dashboard or Slack slash command (Pro+)."
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <V4Badge tone={trainer?.enabled ? "ok" : "warn"}>
          Trainer {trainer?.enabled ? "on" : "off"}
        </V4Badge>
        <V4Badge tone={trainer?.signing_secret_configured ? "ok" : "info"}>
          Signing secret {trainer?.signing_secret_configured ? "set" : "unset"}
        </V4Badge>
        <V4Badge tone={trainer?.tenant_id_configured ? "ok" : "info"}>
          Tenant map {trainer?.tenant_id_configured ? "set" : "unset"}
        </V4Badge>
        <V4Badge tone={ready ? "ok" : "warn"}>
          Slack ingress {ready ? "ready" : "needs env"}
        </V4Badge>
      </div>
      <p className="mb-3 text-xs leading-relaxed text-(--qs-text-3)">
        Configure Slack app slash command →{" "}
        <code className="font-mono text-(--qs-cyan)">
          https://queenswarm.love{trainer?.slash_command_path ?? "/api/v1/harness/slack-trainer/slack-command"}
        </code>
        . Set <code className="font-mono">SLACK_HARNESS_TRAINER_SIGNING_SECRET</code> and{" "}
        <code className="font-mono">SLACK_HARNESS_TRAINER_TENANT_ID</code> in production env.
      </p>
      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        rows={5}
        maxLength={4000}
        className="qs-input min-h-[120px] font-mono text-xs leading-relaxed"
        placeholder={"Always verify simulations before reporting.\nPrefer bullet morning briefings under 200 words."}
      />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-(--qs-text-3)">{feedback.length}/4000</span>
        <button
          type="button"
          disabled={busy}
          onClick={() => void submitFeedback()}
          className="qs-btn qs-btn--primary qs-btn--sm inline-flex items-center gap-1.5"
        >
          {busy ? (
            <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
          ) : (
            <MessageSquarePlusIcon className="h-3.5 w-3.5" aria-hidden />
          )}
          {busy ? "Saving…" : "Append feedback"}
        </button>
      </div>
    </V4Card>
  );
}
