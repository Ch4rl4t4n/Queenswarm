/** Subtle animated amber hex grid behind auth screens (single SVG, unique pattern IDs). */

export function AuthHexBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      <div className="absolute left-1/4 top-1/4 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,#FFB80008_0%,transparent_72%)]" />
      <div className="absolute bottom-1/4 right-1/4 h-96 w-96 translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,#00FFFF06_0%,transparent_72%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_50%,rgba(255,184,0,0.04)_0%,transparent_72%)]" />

      <svg className="auth-hex-layer absolute inset-0 h-[120%] w-[120%] text-pollen/40" preserveAspectRatio="none">
        <defs>
          <pattern id="qs-hex-a" x="0" y="0" width="60" height="69.28" patternUnits="userSpaceOnUse">
            <polygon
              points="30,0 60,17.32 60,51.96 30,69.28 0,51.96 0,17.32"
              fill="none"
              stroke="currentColor"
              strokeWidth="0.8"
              opacity="0.55"
            />
          </pattern>
          <pattern id="qs-hex-b" x="30" y="34.64" width="60" height="69.28" patternUnits="userSpaceOnUse">
            <polygon
              points="30,0 60,17.32 60,51.96 30,69.28 0,51.96 0,17.32"
              fill="none"
              stroke="currentColor"
              strokeWidth="0.8"
              opacity="0.45"
            />
          </pattern>
        </defs>
        <rect x="-10%" y="-10%" width="120%" height="120%" fill="url(#qs-hex-a)" className="opacity-[0.08]" />
        <rect x="-10%" y="-10%" width="120%" height="120%" fill="url(#qs-hex-b)" className="opacity-[0.065]" />
      </svg>
    </div>
  );
}
