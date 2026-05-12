const cfg: Record<
  string,
  {
    label: string;
    emoji: string;
    cls: string;
  }
> = {
  scout: {
    label: "Scout",
    emoji: "🔍",
    cls: "bg-blue-900/30 text-blue-300 border-blue-700/40",
  },
  eval: {
    label: "Eval",
    emoji: "🧠",
    cls: "bg-green-900/30 text-green-300 border-green-700/40",
  },
  sim: {
    label: "Sim",
    emoji: "🎲",
    cls: "bg-amber-900/30 text-amber-300 border-amber-700/40",
  },
  action: {
    label: "Action",
    emoji: "⚡",
    cls: "bg-purple-900/30 text-purple-300 border-purple-700/40",
  },
};

export function SwarmBadge({ swarm }: { swarm: string }) {
  const c =
    cfg[swarm?.toLowerCase()] ?? {
      label: swarm,
      emoji: "🐝",
      cls: "bg-gray-800 text-gray-400 border-gray-700",
    };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${c.cls}`}
    >
      {c.emoji} {c.label}
    </span>
  );
}
