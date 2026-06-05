import { LacIcon } from "@/components/marketing/lac-icons";

interface ScorePillProps {
  readonly score: number | null;
}

export function ScorePill({ score }: ScorePillProps): JSX.Element | null {
  if (score == null) {
    return null;
  }
  return (
    <span className="mk-score">
      <LacIcon name="spark" size={12} />
      Score {score}
    </span>
  );
}
