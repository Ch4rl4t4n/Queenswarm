export function PollenBar({
  value,
  max = 1000,
  showLabel = true,
}: {
  value: number;
  max?: number;
  showLabel?: boolean;
}) {
  const pct = Math.min(100, Math.round((value / max) * 100));

  return (
    <div className="w-full">
      {showLabel ? (
        <div className="flex justify-between text-xs mb-1">
          <span className="text-[#FFB800]">🍯 {value}</span>
          <span className="text-gray-500">{pct}%</span>
        </div>
      ) : null}
      <div className="h-1.5 bg-[#1a1a3e] rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-[#FFB800] to-[#FF00AA] rounded-full transition-all duration-700 shadow-[0_0_6px_#FFB80088]"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
