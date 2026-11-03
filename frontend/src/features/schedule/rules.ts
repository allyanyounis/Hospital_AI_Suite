/** OPD schedule helpers (one doctor's week). The same rules the backend enforces, shown live before saving. */

import type { DaySchedule } from "./types";

export const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export const toMinutes = (hhmm: string) => Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(3, 5));
export const toHHMM = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;

/** JS getDay() is 0 = Sunday; the schedule uses 0 = Monday */
export const weekdayIndex = (d = new Date()) => (d.getDay() + 6) % 7;

export function hoursLabel(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

const sortedBreaks = (day: DaySchedule) => [...day.breaks].sort((a, b) => toMinutes(a.start) - toMinutes(b.start));

export function dayError(day: DaySchedule): string | null {
  if (!day.enabled) return null;
  if (toMinutes(day.end) <= toMinutes(day.start)) return "Finish time must be after start time.";
  let previousEnd = toMinutes(day.start);
  for (const b of sortedBreaks(day)) {
    if (toMinutes(b.end) <= toMinutes(b.start)) return "A break must end after it starts.";
    if (toMinutes(b.start) < previousEnd || toMinutes(b.end) > toMinutes(day.end)) {
      return "Breaks must be inside working hours and must not overlap.";
    }
    previousEnd = toMinutes(b.end);
  }
  return null;
}

/** Minutes worked on a day (breaks excluded). */
export function workMinutes(day: DaySchedule): number {
  if (!day.enabled) return 0;
  const breaks = day.breaks.reduce((sum, b) => sum + Math.max(0, toMinutes(b.end) - toMinutes(b.start)), 0);
  return Math.max(0, toMinutes(day.end) - toMinutes(day.start) - breaks);
}

/** Bookable slots in a day: counted from opening, restarting after each break, each must finish in time. */
export function slotCount(day: DaySchedule, slotMinutes: number): number {
  if (!day.enabled || dayError(day)) return 0;
  const edges = [toMinutes(day.start)];
  sortedBreaks(day).forEach((b) => edges.push(toMinutes(b.start), toMinutes(b.end)));
  edges.push(toMinutes(day.end));
  let count = 0;
  for (let i = 0; i < edges.length; i += 2) count += Math.max(0, Math.floor((edges[i + 1] - edges[i]) / slotMinutes));
  return count;
}

/** A free spot for a new break: lunch at 1 PM if it fits, otherwise the first gap. */
export function suggestBreak(day: DaySchedule): { start: string; end: string } | null {
  const start = toMinutes(day.start);
  const end = toMinutes(day.end);
  const length = end - start >= 180 ? 60 : 30;
  const fits = (s: number) =>
    s >= start && s + length <= end && day.breaks.every((b) => s + length <= toMinutes(b.start) || s >= toMinutes(b.end));
  const candidates = [13 * 60, ...Array.from({ length: Math.ceil((end - start) / 30) }, (_, i) => start + 30 * (i + 1))];
  const found = candidates.find(fits);
  return found === undefined ? null : { start: toHHMM(found), end: toHHMM(found + length) };
}
