/** Appointment data contracts (FastAPI /api/appointments). Booked by the front desk, the voice agent or the portal. */

export type BookingChannel = "voice" | "desk" | "portal";

export const BOOKING_CHANNELS: Record<BookingChannel, string> = {
  voice: "Voice agent",
  desk: "Front desk",
  portal: "Patient portal",
};

export type Appointment = {
  id: number;
  patient_id: number;
  patient_name: string;
  reason: string | null;
  start_time: string;
  canceled: boolean;
  created_at: string;
  booked_via: BookingChannel;
  /** The doctor seen; the department is the doctor's */
  practitioner: { id: number; display_name: string; department: string };
  /** "AI: ..." / "User: ..." lines; null if not booked by a voice call */
  transcript: string | null;
};

/** start_time is hospital-local "YYYY-MM-DDTHH:MM" */
export type NewAppointment = { patient_id: number; practitioner_id: number; start_time: string; reason: string };

/** Free, bookable slot start times ("HH:MM") for one doctor on one date */
export type Availability = { date: string; slots: string[] };

export type LiveEvent = "appointment_booked" | "appointment_canceled" | "transcript_saved" | "schedule_updated";
