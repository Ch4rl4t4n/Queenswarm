const LOADING_HEX_PATH =
  "M 21.809 3.205 Q 24.000 2.000 26.191 3.205 L 41.809 11.795 Q 44.000 13.000 44.000 15.500 L 44.000 32.500 Q 44.000 35.000 41.809 36.205 L 26.191 44.795 Q 24.000 46.000 21.809 44.795 L 6.191 36.205 Q 4.000 35.000 4.000 32.500 L 4.000 15.500 Q 4.000 13.000 6.191 11.795 Z";

export function LoadingHex({ size = 48 }: { size?: number }) {
  return (
    <div className="flex items-center justify-center p-8">
      <svg width={size} height={size} viewBox="0 0 48 48" className="animate-spin">
        <path
          d={LOADING_HEX_PATH}
          fill="none"
          stroke="#FFB800"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="3"
          opacity="0.25"
        />
        <path
          d={LOADING_HEX_PATH}
          fill="none"
          stroke="#FFB800"
          strokeDasharray="64 22"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="3.75"
        />
      </svg>
    </div>
  );
}
