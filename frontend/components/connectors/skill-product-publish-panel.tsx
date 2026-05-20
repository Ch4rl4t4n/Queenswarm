"use client";

import Link from "next/link";
import { CheckCircle2Icon, CopyIcon, ExternalLinkIcon, RocketIcon } from "lucide-react";
import { useCallback } from "react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import type { SkillExportResponse, SkillPublishChannel } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface SkillProductPublishPanelProps {
  bundle: SkillExportResponse;
  className?: string;
}

/** Multi-channel publish checklist after skill export (GitHub, Gumroad, Cursor, Stripe). */
export function SkillProductPublishPanel({ bundle, className }: SkillProductPublishPanelProps): JSX.Element {
  const publish = bundle.publish;

  const copyText = useCallback(async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(`${label} copied.`);
    } catch {
      toast.error("Clipboard unavailable.");
    }
  }, []);

  if (!publish) {
    return (
      <p className={cn("text-sm text-(--qs-text-3)", className)}>
        Publish guide unavailable — re-export the skill to refresh bundle metadata.
      </p>
    );
  }

  return (
    <section className={cn("v4-learning-panel space-y-4 p-4", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <RocketIcon className="h-4 w-4 text-pollen" aria-hidden />
            <p className="text-sm font-medium text-(--qs-text)">Sell anywhere — publish checklist</p>
            <V4Badge tone="ok">{publish.suggested_price_display} suggested</V4Badge>
          </div>
          <p className="text-xs text-(--qs-text-3)">{bundle.install_hint}</p>
        </div>
        <Link href="/ballroom" className="qs-btn qs-btn--ghost qs-btn--sm">
          Open Ballroom
        </Link>
      </div>

      <ol className="space-y-2 text-sm text-(--qs-text-2)">
        {publish.checklist.map((step) => (
          <li key={step} className="flex gap-2">
            <CheckCircle2Icon className="mt-0.5 h-4 w-4 shrink-0 text-cyan" aria-hidden />
            <span>{step}</span>
          </li>
        ))}
      </ol>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {publish.channels.map((channel: SkillPublishChannel) => (
          <article key={channel.id} className="v4-int-card flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
              <p className="v4-int-name">{channel.label}</p>
              {channel.id === "queenswarm" ? (
                <V4Badge tone="info">optional</V4Badge>
              ) : null}
            </div>
            <p className="text-xs text-(--qs-text-3)">{channel.description}</p>
            <div className="mt-auto flex flex-wrap gap-2">
              {channel.action_url ? (
                <a
                  href={channel.action_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                >
                  <ExternalLinkIcon className="h-3.5 w-3.5" aria-hidden /> Open
                </a>
              ) : null}
              {channel.copy_text ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm"
                  onClick={() => void copyText(channel.copy_text ?? "", channel.label)}
                >
                  <CopyIcon className="h-3.5 w-3.5" aria-hidden /> Copy
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>

      <p className="font-mono text-xs text-cyan">{publish.install_command}</p>
      <p className="text-xs text-(--qs-text-3)">
        GitHub target: {publish.github_repo_url}/tree/main/{publish.github_folder_path}
      </p>
    </section>
  );
}
