/** AI receptionist. */

import { http } from "./client";

export type Appointment = {
  id: number;
  patient_name: string;
  reason: string | null;
  start_time: string;
  canceled: boolean;
  created_at: string;
  /** "AI: ..." / "User: ..." lines; null if not booked by a voice call */
  transcript: string | null;
};

export const receptionApi = {
  appointments: () => http.get<Appointment[]>("/api/reception/appointments"),
  cancelAppointment: (id: number) => http.post<Appointment>(`/api/reception/appointments/${id}/cancel`),
};
