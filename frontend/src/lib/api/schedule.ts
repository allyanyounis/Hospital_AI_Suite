/** Clinic schedule, shared by every module. */

import { http } from "./client";

export type BreakPeriod = { start: string; end: string }; // "HH:MM"
export type DaySchedule = { enabled: boolean; start: string; end: string; breaks: BreakPeriod[] };
export type ClinicScheduleInput = { days: DaySchedule[]; slot_minutes: number; holidays: string[] };
export type ClinicSchedule = ClinicScheduleInput & { is_default: boolean; updated_at: string | null };

/** Pushed over the live-events WebSocket when data changes */
export type LiveEvent = "appointment_booked" | "appointment_canceled" | "transcript_saved" | "schedule_updated";

export const scheduleApi = {
  schedule: () => http.get<ClinicSchedule>("/api/schedule"),
  saveSchedule: (schedule: ClinicScheduleInput) => http.put<ClinicSchedule>("/api/schedule", schedule),
};
