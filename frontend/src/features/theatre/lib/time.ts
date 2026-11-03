/** Time-of-day helpers: the planner speaks in minutes after midnight (480 = 08:00) and "YYYY-MM-DD" days. */

export const DAY_OPEN = 480;
export const DAY_CLOSE = 960;

/** 545 -> "09:05" */
export function hm(minutes: number): string {
  const m = Math.max(0, Math.round(minutes));
  return `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

/** 95 -> "1h 35m", 40 -> "40m" */
export function span(minutes: number): string {
  const m = Math.max(0, Math.round(minutes));
  if (m < 60) return `${m}m`;
  return m % 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m / 60}h`;
}

/** "YYYY-MM-DD" -> local Date at midnight */
export const dateOf = (day: string) => new Date(`${day}T00:00:00`);

export const dayLabel = (day: string, opts: Intl.DateTimeFormatOptions = { weekday: "short", month: "short", day: "numeric" }) =>
  dateOf(day).toLocaleDateString("en-US", opts);

/** "YYYY-MM-DD" shifted by whole days */
export function addDays(day: string, n: number): string {
  const d = dateOf(day);
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Next weekday on or after `day` (skips Saturday/Sunday), moving in `step` direction */
export function weekday(day: string, step: 1 | -1 = 1): string {
  let d = day;
  while ([0, 6].includes(dateOf(d).getDay())) d = addDays(d, step);
  return d;
}

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
