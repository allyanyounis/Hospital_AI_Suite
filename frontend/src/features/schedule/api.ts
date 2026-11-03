import { http } from "@/shared/api/http";
import type { Closure, DoctorSchedule, DoctorScheduleInput } from "./types";

export const scheduleApi = {
  doctorSchedule: (staffId: number) => http.get<DoctorSchedule>(`/api/schedules/${staffId}`),
  saveDoctorSchedule: (staffId: number, schedule: DoctorScheduleInput) =>
    http.put<DoctorSchedule>(`/api/schedules/${staffId}`, schedule),
  closures: () => http.get<Closure[]>("/api/closures"),
  saveClosures: (closures: Closure[]) => http.put<Closure[]>("/api/closures", { closures }),
};
