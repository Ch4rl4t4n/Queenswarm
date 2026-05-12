export function LoadingHex({ size = 48 }: { size?: number }) {
  return (
    <div className="flex items-center justify-center p-8">
      <svg width={size} height={size} viewBox="0 0 48 48" className="animate-spin">
        <polygon
          points="24,2 44,13 44,35 24,46 4,35 4,13"
          fill="none"
          stroke="#FFB800"
          strokeWidth="1.5"
          opacity="0.25"
        />
        <polygon
          points="24,2 44,13 44,35 24,46 4,35 4,13"
          fill="none"
          stroke="#FFB800"
          strokeWidth="2"
          strokeDasharray="60 20"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
