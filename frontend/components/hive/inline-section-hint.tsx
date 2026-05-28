import type { ReactNode } from "react";

import { InfoHint } from "@/components/hive/info-hint";
import { sectionHintProps, type SectionHintKey } from "@/lib/section-hints";
import type { MaybeLocalizedString, MaybeLocalizedStringList } from "@/lib/ui-language";
import { cn } from "@/lib/utils";

export interface InlineSectionHintProps {
  title: MaybeLocalizedString;
  description: MaybeLocalizedString;
  options?: MaybeLocalizedStringList;
  manualHref?: string;
  className?: string;
}

/** Info `(i)` inline at end of section description — always use `hive-inline-hint`. */
export function InlineSectionHint({
  title,
  description,
  options,
  manualHref,
  className,
}: InlineSectionHintProps): ReactNode {
  return (
    <InfoHint
      title={title}
      description={description}
      options={options}
      manualHref={manualHref}
      className={cn("hive-inline-hint", className)}
    />
  );
}

/** Render hint from central registry by key. */
export function InlineSectionHintKey({ hintKey }: { hintKey: SectionHintKey }): ReactNode {
  const hint = sectionHintProps(hintKey);
  return (
    <InlineSectionHint
      title={hint.title}
      description={hint.description}
      options={hint.options}
      manualHref={hint.manualHref}
    />
  );
}

/** ReactNode helper for V4CardHeader `hint` prop. */
export function sectionHintNode(key: SectionHintKey): ReactNode {
  return <InlineSectionHintKey hintKey={key} />;
}
