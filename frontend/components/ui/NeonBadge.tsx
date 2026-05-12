type V = "amber" | "cyan" | "green" | "magenta" | "red" | "gray";

const v: Record<V, string> = {
  amber: "bg-[#FFB800]/10 text-[#FFB800] border-[#FFB800]/30",
  cyan: "bg-[#00FFFF]/10 text-[#00FFFF] border-[#00FFFF]/30",
  green: "bg-[#00FF88]/10 text-[#00FF88] border-[#00FF88]/30",
  magenta: "bg-[#FF00AA]/10 text-[#FF00AA] border-[#FF00AA]/30",
  red: "bg-[#FF3366]/10 text-[#FF3366] border-[#FF3366]/30",
  gray: "bg-gray-800 text-gray-400 border-gray-700",
};

export function NeonBadge({ label, variant = "amber" }: { label: string; variant?: V }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border font-mono ${v[variant]}`}
    >
      {label}
    </span>
  );
}
