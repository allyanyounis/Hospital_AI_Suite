/**
 * Appointments feature: the hospital's OPD appointments (/appointments) from every channel (front desk, voice agent,
 * patient portal), front-desk booking, live booking events and the helpers the dashboard uses.
 * Public API of the module: import from "@/features/appointments", never from its internal files.
 */

export { AppointmentsView } from "./views/AppointmentsView";
export { UpcomingChart } from "./components/UpcomingChart";
export { isUpcoming, nextUp, todaysActive, topReasons } from "./helpers";
export { useAppointments, useLiveEvents } from "./hooks";
export { BOOKING_CHANNELS } from "./types";
export type * from "./types";
