import { http } from "@/shared/api/http";
import type { Appointment, Availability, NewAppointment } from "./types";

export const appointmentsApi = {
  list: () => http.get<Appointment[]>("/api/appointments"),
  /** Rule failures (slot taken, outside hours, closed date) come back as a readable error message */
  book: (appointment: NewAppointment) => http.post<Appointment>("/api/appointments", appointment),
  cancel: (id: number) => http.post<Appointment>(`/api/appointments/${id}/cancel`),
  availability: (practitionerId: number, date: string) =>
    http.get<Availability>(`/api/appointments/availability?practitioner_id=${practitionerId}&date=${date}`),
};
