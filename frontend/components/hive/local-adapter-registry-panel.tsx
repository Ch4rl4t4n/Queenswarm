"use client";

import { LayersIcon, Loader2Icon, Trash2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";

interface LocalAdapterRow {
  id: string;
  name: string;
  ollama_tag: string;
  litellm_slug: string;
  kind: "gguf" | "lora";
  is_active: boolean;
}

interface LocalAdapterSnapshot {
  enabled: boolean;
  adapters: LocalAdapterRow[];
  active_slug: string | null;
  operator_hint: string;
}

/** Settings panel — tenant LoRA/GGUF adapter registry (Track M LOC8). */
export function LocalAdapterRegistryPanel(): JSX.Element | null {
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<LocalAdapterSnapshot | null>(null);
  const [disabled, setDisabled] = useState(false);
  const [name, setName] = useState("");
  const [ollamaTag, setOllamaTag] = useState("");

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<LocalAdapterSnapshot>("llm-routing/local-adapters");
      setSnapshot(body);
      setDisabled(false);
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 404) {
        setDisabled(true);
      } else {
        toast.error(e instanceof HiveApiError ? e.message : "Local adapter registry unavailable.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const register = useCallback(async () => {
    if (!name.trim() || !ollamaTag.trim()) {
      toast.error("Name and Ollama tag required.");
      return;
    }
    setBusyId("register");
    try {
      await hivePostJson("llm-routing/local-adapters", {
        name: name.trim(),
        ollama_tag: ollamaTag.trim(),
        kind: "gguf",
        activate: true,
      });
      toast.success("Adapter registered.");
      setName("");
      setOllamaTag("");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Register failed.");
    } finally {
      setBusyId(null);
    }
  }, [load, name, ollamaTag]);

  const activate = useCallback(
    async (adapterId: string) => {
      setBusyId(adapterId);
      try {
        await hivePostJson(`llm-routing/local-adapters/${adapterId}/activate`, {});
        toast.success("Adapter activated.");
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Activate failed.");
      } finally {
        setBusyId(null);
      }
    },
    [load],
  );

  const remove = useCallback(
    async (adapterId: string) => {
      setBusyId(adapterId);
      try {
        await hiveDelete(`llm-routing/local-adapters/${adapterId}`);
        toast.success("Adapter removed from registry.");
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Delete failed.");
      } finally {
        setBusyId(null);
      }
    },
    [load],
  );

  if (disabled) {
    return null;
  }

  return (
    <div data-testid="local-adapter-registry-panel">
      <V4Card className="v4-card-interactive border-pollen/25">
        <V4CardHeader
          title="Local adapter registry"
          description="Register Unsloth/Ollama tags for local_sovereign routing (LOC8)."
          actions={
            snapshot?.active_slug ? (
              <V4Badge tone="ok">{snapshot.active_slug}</V4Badge>
            ) : (
              <LayersIcon className="h-4 w-4 text-pollen" aria-hidden />
            )
          }
        />

        {loading ? (
          <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading adapters…
          </p>
        ) : null}

        {snapshot ? (
          <div className="space-y-4">
            {snapshot.adapters.length > 0 ? (
              <ul className="space-y-2 text-sm">
                {snapshot.adapters.map((row) => (
                  <li
                    key={row.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-pollen/20 px-3 py-2"
                  >
                    <div>
                      <span className="font-medium">{row.name}</span>
                      <span className="ml-2 font-mono text-xs text-cyan">{row.litellm_slug}</span>
                      {row.is_active ? (
                        <span className="ml-2 text-xs text-success">active</span>
                      ) : null}
                    </div>
                    <div className="flex gap-2">
                      {!row.is_active ? (
                        <button
                          type="button"
                          disabled={busyId === row.id}
                          onClick={() => void activate(row.id)}
                          className="rounded border border-success/40 px-2 py-1 text-xs text-success"
                        >
                          Activate
                        </button>
                      ) : null}
                      <button
                        type="button"
                        disabled={busyId === row.id}
                        onClick={() => void remove(row.id)}
                        className="inline-flex items-center gap-1 rounded border border-error/30 px-2 py-1 text-xs text-error"
                        aria-label={`Remove ${row.name}`}
                      >
                        <Trash2Icon className="h-3 w-3" aria-hidden />
                        Remove
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-(--qs-text-3)">No adapters registered — import via Unsloth bridge first.</p>
            )}

            <div className="grid gap-2 sm:grid-cols-2">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Display name"
                className="rounded-md border border-(--qs-border) bg-(--qs-surface-2) px-3 py-2 text-sm"
              />
              <input
                type="text"
                value={ollamaTag}
                onChange={(e) => setOllamaTag(e.target.value)}
                placeholder="Ollama tag (e.g. queenswarm-v1)"
                className="rounded-md border border-(--qs-border) bg-(--qs-surface-2) px-3 py-2 text-sm font-mono"
              />
            </div>
            <button
              type="button"
              disabled={busyId === "register"}
              onClick={() => void register()}
              className="rounded-md border border-pollen/40 px-3 py-2 text-sm text-pollen hover:bg-pollen/10 disabled:opacity-50"
            >
              Register adapter
            </button>
            <p className="text-xs text-(--qs-text-3)">{snapshot.operator_hint}</p>
          </div>
        ) : null}
      </V4Card>
    </div>
  );
}
