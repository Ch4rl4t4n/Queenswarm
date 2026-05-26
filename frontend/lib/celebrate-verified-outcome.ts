/** Pollen confetti burst for verified operator outcomes (Execution Studio confirm, simulation pass). */

export async function celebrateVerifiedOutcome(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }
  try {
    const confetti = (await import("canvas-confetti")).default;
    confetti({
      particleCount: 72,
      spread: 62,
      origin: { y: 0.72 },
      colors: ["#FFB800", "#00FF88", "#00FFFF"],
      disableForReducedMotion: true,
    });
  } catch {
    /* optional dependency — skip if unavailable */
  }
}
