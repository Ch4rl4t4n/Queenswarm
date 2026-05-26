"use client";

import { Shield } from "lucide-react";
import { memo, useCallback, useState } from "react";

import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { HiveApiError, hivePatchJson } from "@/lib/api";
import type { ExecutionMode, StudioPolicy } from "@/lib/execution-studio-shared-types";

export interface ExecutionStudioPolicyPanelProps {
  policy: StudioPolicy;
  loading: boolean;
  onPolicyUpdate: (policy: StudioPolicy) => void;
  onError: (message: string | null) => void;
}

function ExecutionStudioPolicyPanelInner({
  policy,
  loading,
  onPolicyUpdate,
  onError,
}: ExecutionStudioPolicyPanelProps) {
  const [busy, setBusy] = useState(false);

  const patchPolicy = useCallback(
    async (patch: Partial<StudioPolicy>) => {
      setBusy(true);
      onError(null);
      try {
        const resp = await hivePatchJson<{ policy: StudioPolicy }>("execution-studio/policy", patch);
        onPolicyUpdate(resp.policy);
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Policy update failed.");
      } finally {
        setBusy(false);
      }
    },
    [onError, onPolicyUpdate],
  );

  return (
    <div className="qs-bubble shrink-0 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold text-(--qs-text)">
            <Shield className="h-4 w-4 text-cyan" aria-hidden />
            Execution policy
          </p>
          <p className="mt-1 text-xs text-(--qs-text-3)">
            Agents inherit this default when a task includes external execution. Live writes can require supervisor
            approval.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <QsSelect
            className="min-w-[11rem]"
            value={policy.default_mode ?? "simulate"}
            disabled={busy || loading}
            onValueChange={(next) => void patchPolicy({ default_mode: next as ExecutionMode })}
            options={[
              { value: "draft", label: "Draft" },
              { value: "simulate", label: "Simulate" },
              { value: "live", label: "Live" },
            ]}
          />
          <label className="flex items-center gap-2 text-xs text-(--qs-text-2)">
            <HiveSwitch
              checked={policy.live_requires_approval ?? true}
              disabled={busy || loading}
              onCheckedChange={(checked) => void patchPolicy({ live_requires_approval: checked })}
            />
            Live approval for writes
          </label>
        </div>
      </div>
    </div>
  );
}

export const ExecutionStudioPolicyPanel = memo(ExecutionStudioPolicyPanelInner);
