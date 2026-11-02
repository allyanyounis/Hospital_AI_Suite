/** Derived numbers and helpers for the AI receptionist's appointments. */

import type { Appointment, ClinicSchedule } from "@/lib/api";
import { dayOffset, nextDays, startOfDay, toDateKey } from "@/lib/format";
import { weekdayIndex } from "@/lib/schedule";

const DAY_MS = 86_400_000;

export type Trend = { current: number; previous: number; percent: number | null };

const trend = (current: number, previous: number): Trend => ({
  current,
  previous,
  percent: previous > 0 ? Math.round(((current - previous) / previous) * 100) : null,
});

const bookedBetween = (list: Appointment[], from: Date, to: Date) =>
  list.filter((a) => {
    const created = new Date(a.created_at);
    return created >= from && created < to;
  }).length;

/** Bookings made today vs yesterday. */
export function dayTrend(list: Appointment[]): Trend {
  const today = startOfDay(new Date());
  return trend(
    bookedBetween(list, today, new Date(today.getTime() + DAY_MS)),
    bookedBetween(list, new Date(today.getTime() - DAY_MS), today),
  );
}

/** Bookings made in the last 7 days vs the 7 before. */
export function weekTrend(list: Appointment[]): Trend {
  const end = new Date(startOfDay(new Date()).getTime() + DAY_MS);
  const weekAgo = new Date(end.getTime() - 7 * DAY_MS);
  return trend(bookedBetween(list, weekAgo, end), bookedBetween(list, new Date(end.getTime() - 14 * DAY_MS), weekAgo));
}

export const isUpcoming = (a: Appointment, now = new Date()) => !a.canceled && new Date(a.start_time) >= now;

export function todaysActive(list: Appointment[]): Appointment[] {
  return list.filter((a) => !a.canceled && dayOffset(new Date(a.start_time)) === 0);
}

export function nextUp(list: Appointment[], now = new Date()): Appointment | undefined {
  return list
    .filter((a) => isUpcoming(a, now))
    .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())[0];
}

/** Active bookings per day over the next `days` days, flagging closed days and holidays. */
export function upcomingByDay(list: Appointment[], schedule: ClinicSchedule | null, days = 10) {
  return nextDays(days).map((date) => {
    const key = toDateKey(date);
    const holiday = schedule?.holidays.includes(key) ?? false;
    const dayOff = schedule ? !schedule.days[weekdayIndex(date)].enabled : false;
    return {
      key,
      label: date.toLocaleDateString(undefined, { weekday: "short", day: "numeric" }),
      count: list.filter((a) => !a.canceled && toDateKey(new Date(a.start_time)) === key).length,
      closed: holiday ? "Holiday" : dayOff ? "Closed" : null,
    };
  });
}

/** Most common visit reasons among active bookings. */
export function topReasons(list: Appointment[], limit = 5) {
  const counts = new Map<string, { title: string; count: number }>();
  for (const a of list) {
    if (a.canceled) continue;
    const raw = (a.reason || "General Consultation").trim();
    const entry = counts.get(raw.toLowerCase());
    if (entry) entry.count++;
    else counts.set(raw.toLowerCase(), { title: raw.replace(/\b\w/g, (c) => c.toUpperCase()), count: 1 });
  }
  return [...counts.values()].sort((x, y) => y.count - x.count || x.title.localeCompare(y.title)).slice(0, limit);
}

/** Split a stored "AI: ... / User: ..." call transcript into chat turns. */
export function parseCallTranscript(text: string): { role: "ai" | "user"; text: string }[] {
  const turns: { role: "ai" | "user"; text: string }[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    const match = line.match(/^(AI|Assistant|Bot|User|Customer)\s*:\s*(.*)$/i);
    if (match) turns.push({ role: /^(user|customer)$/i.test(match[1]) ? "user" : "ai", text: match[2] });
    else if (turns.length) turns[turns.length - 1].text += ` ${line}`;
    else turns.push({ role: "ai", text: line });
  }
  return turns;
}
