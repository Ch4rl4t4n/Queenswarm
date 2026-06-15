import { LacIcon } from "@/components/marketing/lac-icons";

interface ScorecardBadgeProps {
  readonly score: number | null;
  readonly verdict?: string | null;
  readonly clean?: boolean;
  readonly compact?: boolean;
}

/** REV3 — scorecard-clean badge for catalog and product detail. */
export function ScorecardBadge({
  score,
  verdict,
  clean = false,
  compact = false,
}: ScorecardBadgeProps): JSX.Element | null {
  if (score == null) {
    return null;
  }

  const label = clean
    ? `${score}/100 Verified`
    : verdict
      ? `${score}/100 ${verdict.replace("_", " ")}`
      : `Score ${score}`;

  return (
    <span
      className={`mk-score${clean ? " mk-score--clean" : ""}`}
      title={
        clean
          ? "Scorecard-clean listing — simulate-first verified before sale"
          : "Quality score from simulate-first verification run"
      }
    >
      <LacIcon name={clean ? "shield" : "spark"} size={12} />
      {compact && clean ? "Verified" : label}
    </span>
  );
}
