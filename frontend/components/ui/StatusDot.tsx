type S = "active" | "idle" | "error" | "paused";

const c: Record<S, string> = {
  active: "bg-[#00FF88] shadow-[0_0_8px_#00FF88]",
  idle: "bg-[#FFB800] shadow-[0_0_8px_#FFB800]",
  error: "bg-[#FF3366] shadow-[0_0_8px_#FF3366]",
  paused: "bg-gray-600",
};

export function StatusDot({ status, size = "md" }: { status: S; size?: "sm" | "md" }) {
  return (
    <span
      className={`inline-block rounded-full animate-pulse ${size === "sm" ? "w-2 h-2" : "w-3 h-3"} ${c[status]}`}
      aria-hidden
    />
  );
}
