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
    cyan: "text-cyan-300",
    emerald: "text-emerald-300",
    yellow: "text-yellow-300",
    red: "text-red-300",
    purple: "text-purple-300",
    zinc: "text-zinc-200",
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 shadow-xl shadow-black/20">
      <CardContent className="p-5">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{label}</p>
        <p className={`mt-3 text-3xl font-black ${colors[tone]}`}>{value}</p>
        {hint && <p className="mt-2 text-xs text-zinc-500">{hint}</p>}
      </CardContent>
    </Card>
  );
}
