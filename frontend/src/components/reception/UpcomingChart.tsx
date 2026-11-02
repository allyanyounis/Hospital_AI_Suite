"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Appointment, ClinicSchedule } from "@/lib/api";
import { upcomingByDay } from "@/lib/appointments";
import { useMounted } from "@/lib/hooks";
import { CHART } from "@/lib/theme";

/** Active bookings per day for the next 10 days; closed days and holidays in amber. */
export function UpcomingChart({ appointments, schedule }: { appointments: Appointment[]; schedule: ClinicSchedule | null }) {
  // Recharts measures its container synchronously, so render only after mount
  const mounted = useMounted();
  const data = upcomingByDay(appointments, schedule);

  return (
    <div className="h-[260px] w-full">
      {mounted && (
        <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 1, height: 260 }}>
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART.grid} />
            <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: CHART.axis, fontSize: 12 }} />
            <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: CHART.axis, fontSize: 12 }} />
            <Tooltip
              cursor={{ fill: CHART.primarySoft, opacity: 0.5 }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload as (typeof data)[number];
                return (
                  <div className="rounded-md border border-slate-100 bg-white px-3 py-2 text-xs shadow-sm">
                    <p className="text-slate-500">{d.label}</p>
                    <p className="font-semibold text-slate-900">
                      {d.count} appointment{d.count === 1 ? "" : "s"}
                      {d.closed && (
                        <span className="ml-2 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] uppercase text-amber-700">
                          {d.closed}
                        </span>
                      )}
                    </p>
                  </div>
                );
              }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40} minPointSize={4}>
              {data.map((d) => (
                <Cell key={d.key} fill={d.closed ? CHART.accent : CHART.primary} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
