/** OPD scheduling data contracts (FastAPI /api/schedules/{staff_id}, /api/closures). Each bookable doctor has a week. */

export type BreakPeriod = { start: string; end: string }; // "HH:MM"
export type DaySchedule = { enabled: boolean; start: string; end: string; breaks: BreakPeriod[] };

/** What a doctor's week looks like: 7 days (Monday first) and the appointment slot length */
export type DoctorScheduleInput = { days: DaySchedule[]; slot_minutes: number };
export type DoctorSchedule = DoctorScheduleInput & {
  staff_id: number;
  /** True until someone saves this doctor's week (the default Mon–Fri 09:00–17:00 applies) */
  is_default: boolean;
  updated_at: string | null;
};

/** A date the whole hospital's OPD is closed (holiday); nobody can be booked */
export type Closure = { date: string; reason: string };
