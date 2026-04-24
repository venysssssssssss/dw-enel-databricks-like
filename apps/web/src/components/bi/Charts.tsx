import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { chartPalette } from "../../lib/tokens";

type ChartProps = {
  data: object[];
  xKey: string;
  yKey: string;
  color?: string;
  height?: number;
};

export function VolumeBars({ data, xKey, yKey, color, height = 280 }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey={xKey} stroke="var(--text-muted)" style={{ fontSize: 11 }} />
        <YAxis stroke="var(--text-muted)" style={{ fontSize: 11 }} />
        <Tooltip
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            color: "var(--text)",
            fontSize: 12
          }}
        />
        <Bar dataKey={yKey} radius={[4, 4, 0, 0]}>
          {data.map((_, idx) => (
            <Cell key={idx} fill={color ?? chartPalette[idx % chartPalette.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TrendLine({ data, xKey, yKey, color, height = 280 }: ChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey={xKey} stroke="var(--text-muted)" style={{ fontSize: 11 }} />
        <YAxis stroke="var(--text-muted)" style={{ fontSize: 11 }} />
        <Tooltip
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            color: "var(--text)",
            fontSize: 12
          }}
        />
        <Line
          type="monotone"
          dataKey={yKey}
          stroke={color ?? chartPalette[0]}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
