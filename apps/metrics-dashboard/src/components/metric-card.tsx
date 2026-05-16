import { Card, CardContent } from "@/components/ui/card";

const tones = {
  cyan: {
    accent: "text-cyan-200",
    glow: "from-cyan-300/20",
  },
  emerald: {
    accent: "text-emerald-200",
    glow: "from-emerald-300/20",
  },
  yellow: {
    accent: "text-yellow-200",
    glow: "from-yellow-300/20",
  },
  red: {
    accent: "text-red-200",
    glow: "from-red-300/20",
  },
  purple: {
    accent: "text-purple-200",
    glow: "from-purple-300/20",
  },
  zinc: {
    accent: "text-zinc-200",
    glow: "from-zinc-300/10",
  },
} as const;

export function MetricCard({
  label,
  value,
  hint,
  tone = "cyan",
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "cyan" | "emerald" | "yellow" | "red" | "purple" | "zinc";
}) {
  const toneStyles = tones[tone];

  return (
    <Card className={`relative overflow-hidden border-zinc-800/90 bg-gradient-to-br ${toneStyles.glow} to-zinc-950/90 shadow-xl shadow-black/20 before:absolute before:inset-y-4 before:left-0 before:w-1 before:rounded-r-full before:bg-current ${toneStyles.accent}`}>
      <CardContent className="p-5 pl-6">
        <p className="font-mono text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-zinc-500">{label}</p>
        <p className={`mt-3 text-3xl font-bold tracking-[-0.04em] ${toneStyles.accent}`}>{value}</p>
        {hint && <p className="mt-2 font-mono text-xs text-zinc-500">{hint}</p>}
      </CardContent>
    </Card>
  );
}
