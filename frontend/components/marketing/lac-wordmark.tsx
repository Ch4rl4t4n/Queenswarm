import Link from "next/link";

interface LacWordmarkProps {
  readonly showTagline?: boolean;
}

export function LacWordmark({ showTagline = true }: LacWordmarkProps): JSX.Element {
  return (
    <Link href="/" className="mk-brand">
      <div>
        <div className="mk-name wordmark-grad">Let Agents Cook</div>
        {showTagline ? <div className="mk-sub">Verified Skills</div> : null}
      </div>
    </Link>
  );
}
