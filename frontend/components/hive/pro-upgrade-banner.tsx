"use client";

interface ProUpgradeBannerProps {
  className?: string;
  /** Short reason shown beside the CTA. */
  reason?: string;
}

/** Legacy commercial upsell banner removed with checkout sunset. */
export function ProUpgradeBanner({ className, reason }: ProUpgradeBannerProps): JSX.Element | null {
  void className;
  void reason;
  return null;
}
