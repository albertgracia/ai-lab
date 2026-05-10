import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";

export default function HistoryCharts() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch("/api/history.json")
      .then((r) => r.json())
      .then((json) => {
        const rows = [];

        for (const snap of json.snapshots || []) {
          for (const gpu of snap.gpu || []) {
            rows.push({
              timestamp: snap.timestamp,
              node: gpu.node,
              usage: gpu.usage || 0,
              vram_used: gpu.vram_used || 0,
            });
          }
        }

        setData(rows);
      });
  }, []);

  return (
    <div className="space-y-10">

      <div>
        <h2 className="text-2xl font-bold mb-4">
          GPU Usage %
        </h2>

        <div className="h-[320px] bg-black/20 rounded-xl p-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" hide />
              <YAxis />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="usage"
                stroke="#3b82f6"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <h2 className="text-2xl font-bold mb-4">
          VRAM Usage (GiB)
        </h2>

        <div className="h-[320px] bg-black/20 rounded-xl p-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" hide />
              <YAxis />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="vram_used"
                stroke="#22c55e"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}
