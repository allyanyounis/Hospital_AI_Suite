/** Derived numbers and helpers for appointments (dashboard, appointments board, voice agent). */

import type { Closure } from "@/features/schedule";
import { dayOffset, nextDays, toDateKey } from "@/shared/lib/format";
import type { Appointment } from "./types";

export const isUpcoming = (a: Appointment, now = new Date()) => !a.canceled && new Date(a.start_time) >= now;

export function todaysActive(list: Appointment[]): Appointment[] {
  return list.filter((a) => !a.canceled && dayOffset(new Date(a.start_time)) === 0);
}

export function nextUp(list: Appointment[], now = new Date()): Appointment | undefined {
  return list
    .filter((a) => isUpcoming(a, now))
    .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())[0];
}

/** Active bookings per day over the next `days` days, flagging the hospital's closed dates. */
export function upcomingByDay(list: Appointment[], closures: Closure[] | null, days = 10) {
  return nextDays(days).map((date) => {
    const key = toDateKey(date);
    const closure = closures?.find((c) => c.date === key);
    return {
      key,
      label: date.toLocaleDateString(undefined, { weekday: "short", day: "numeric" }),
      count: list.filter((a) => !a.canceled && toDateKey(new Date(a.start_time)) === key).length,
      closed: closure ? closure.reason || "Closed" : null,
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
