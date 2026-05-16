"use client";

import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SeriesPoint } from "@/lib/api";

const palette = ["#22d3ee", "#34d399", "#facc15", "#c084fc", "#fb7185", "#60a5fa"];

export function TelemetryChart({ data, labels }: { data: SeriesPoint[]; labels: string[] }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!data.length) {
    return <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 text-sm text-zinc-500">Esperando histórico Prometheus...</div>;
  }

  if (!mounted) {
    return <div className="h-72 rounded-xl border border-zinc-800 bg-black/20" />;
  }

  return (
    <div className="h-72 w-full min-w-0 rounded-2xl border border-zinc-800/80 bg-black/20 p-3">
      <div className="mb-3 flex flex-wrap gap-2">
        {labels.map((label, index) => (
          <span key={label} className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-[11px] font-mono text-zinc-300">
            <span className="mr-2 inline-block h-2 w-2 rounded-full" style={{ background: palette[index % palette.length] }} />
            {label}
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
          <XAxis dataKey="time" stroke="#71717a" tickLine={false} axisLine={false} fontSize={12} />
          <YAxis stroke="#71717a" tickLine={false} axisLine={false} fontSize={12} width={42} />
          <Tooltip
            contentStyle={{ background: "#09090b", border: "1px solid #27272a", borderRadius: "12px", color: "#e4e4e7" }}
            labelStyle={{ color: "#67e8f9" }}
          />
          {labels.map((label, index) => (
            <Line key={label} type="monotone" dataKey={label} stroke={palette[index % palette.length]} strokeWidth={2} dot={false} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
