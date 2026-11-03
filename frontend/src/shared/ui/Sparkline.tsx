"use client";

import { Line, LineChart, ReferenceArea, ResponsiveContainer, YAxis } from "recharts";
import { useMounted } from "@/shared/hooks";
import { CHART } from "@/shared/lib/theme";

/**
 * A tiny trend line (no axes, grid or tooltip) that fills its container's width, e.g. a vital sign over the last
 * hours. `low`/`high` shade the normal range behind the line; nulls in `values` leave a gap.
 */
export function Sparkline({
  values,
  low,
  high,
  color = CHART.primary,
  height = 32,
  className = "",
}: {
  values: (number | null)[];
  low?: number;
  high?: number;
  color?: string;
  height?: number;
  className?: string;
}) {
  // Recharts measures its container synchronously, so render only after mount
  const mounted = useMounted();
  const data = values.map((value, i) => ({ i, value }));
  const numbers = values.filter((v): v is number => v != null);
  const band = [low, high].filter((v): v is number => v != null);
  const all = [...numbers, ...band];
  const domain: [number, number] = all.length ? [Math.min(...all), Math.max(...all)] : [0, 1];
  if (domain[0] === domain[1]) domain[1] = domain[0] + 1;

  return (
    <div className={`w-full ${className}`} style={{ height }}>
      {mounted && (
        <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 1, height }}>
          <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
            <YAxis hide domain={domain} />
            {(low != null || high != null) && (
              <ReferenceArea
                y1={low ?? domain[0]}
                y2={high ?? domain[1]}
                fill={CHART.band}
                fillOpacity={0.7}
                stroke="none"
                ifOverflow="extendDomain"
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
