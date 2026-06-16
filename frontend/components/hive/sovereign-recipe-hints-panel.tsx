"use client";

import { BookOpenIcon, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface SovereignRecipeHint {
  recipe_id: string;
  name: string;
  topic_tags: string[];
  success_rate: number;
  imitation_hint: string;
}

interface SovereignRecipeHintsSnapshot {
  enabled: boolean;
  sovereign_mode: boolean;
  imitation_boost: number;
  local_adapter_recipe_count: number;
  hints: SovereignRecipeHint[];
  operator_hint: string;
}

/** Settings panel — LOC14 local-adapter recipe imitation hints. */
export function SovereignRecipeHintsPanel(): JSX.Element | null {
  const [loading, setLoading] = useState(true);
  const [disabled, setDisabled] = useState(false);
  const [snapshot, setSnapshot] = useState<SovereignRecipeHintsSnapshot | null>(null);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<SovereignRecipeHintsSnapshot>("llm-routing/sovereign-recipe-hints");
      setSnapshot(body);
      setDisabled(false);
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 404) {
        setDisabled(true);
      } else {
        toast.error(e instanceof HiveApiError ? e.message : "Sovereign recipe hints unavailable.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (disabled) {
    return null;
  }

  if (loading) {
    return (
      <V4Card className="mt-6">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Loading sovereign recipe hints…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <div data-testid="sovereign-recipe-hints-panel">
      <V4Card className="mt-6">
        <V4CardHeader
          title="Sovereign recipe hints · local-adapter"
          description={
            snapshot.sovereign_mode
              ? `Imitation boost +${Math.round(snapshot.imitation_boost * 100)}% on tagged recipes`
              : "Switch to local_sovereign routing to activate boost"
          }
          leadingIcon={BookOpenIcon}
          leadingIconTone="purple"
        />
        <p className="px-4 pb-2 text-xs text-(--qs-text-3)">{snapshot.operator_hint}</p>
        {snapshot.hints.length === 0 ? (
          <p className="px-4 pb-4 text-sm text-(--qs-text-3)">
            No recipes tagged yet — link recipe UUIDs when registering a local adapter.
          </p>
        ) : (
          <ul className="space-y-2 px-4 pb-4">
            {snapshot.hints.map((hint) => (
              <li
                key={hint.recipe_id}
                className="rounded-md border border-(--qs-border-subtle) bg-(--qs-surface-1)/40 p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-(--qs-text-1)">{hint.name}</span>
                  <V4Badge tone="gold">local-adapter</V4Badge>
                  <span className="font-mono text-xs text-(--qs-text-3)">
                    {Math.round(hint.success_rate * 100)}% success
                  </span>
                </div>
                <p className="mt-1 text-xs text-(--qs-text-3)">{hint.imitation_hint}</p>
              </li>
            ))}
          </ul>
        )}
      </V4Card>
    </div>
  );
}
