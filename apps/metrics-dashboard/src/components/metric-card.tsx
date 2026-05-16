import { Card, CardContent } from "@/components/ui/card";

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
  const colors = {
    cyan: "text-cyan-200 from-cyan-300/20",
    emerald: "text-emerald-200 from-emerald-300/20",
    yellow: "text-yellow-200 from-yellow-300/20",
    red: "text-red-200 from-red-300/20",
    purple: "text-purple-200 from-purple-300/20",
    zinc: "text-zinc-200",
  };

  return (
    <Card className={`relative border-zinc-800/90 bg-gradient-to-br ${colors[tone].split(" ").find((className) => className.startsWith("from-")) || "from-zinc-300/10"} to-zinc-950/90 shadow-xl shadow-black/20 before:absolute before:inset-y-4 before:left-0 before:w-1 before:rounded-r-full before:bg-current ${colors[tone].split(" ")[0]}`}>
      <CardContent className="p-5 pl-6">
        <p className="font-mono text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-zinc-500">{label}</p>
        <p className={`mt-3 text-3xl font-bold tracking-[-0.04em] ${colors[tone].split(" ")[0]}`}>{value}</p>
        {hint && <p className="mt-2 font-mono text-xs text-zinc-500">{hint}</p>}
      </CardContent>
    </Card>
  );
}
