/**
 * Schedule feature: each doctor's OPD week (hours, breaks, slot length) and the hospital's closed dates
 * (/schedule). Appointment booking, the voice agent and the scribe's after-hours metric all follow these.
 * Public API of the module: import from "@/features/schedule", never from its internal files.
 */

export { SchedulerView } from "./views/SchedulerView";
export { scheduleApi } from "./api";
export { weekdayIndex } from "./rules";
export type * from "./types";
