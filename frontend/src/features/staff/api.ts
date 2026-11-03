import { http } from "@/shared/api/http";
import type { StaffFilter, StaffMember, StaffProfileInput } from "./types";

function query(filter: StaffFilter): string {
  const params = new URLSearchParams();
  if (filter.department_id != null) params.set("department_id", String(filter.department_id));
  if (filter.bookable != null) params.set("bookable", String(filter.bookable));
  const text = params.toString();
  return text ? `?${text}` : "";
}

export const staffApi = {
  list: (filter: StaffFilter = {}) => http.get<StaffMember[]>(`/api/staff${query(filter)}`),
  /** Doctors patients can book: they have OPD schedules and appointments */
  doctors: () => http.get<StaffMember[]>("/api/staff?bookable=true"),
  saveProfile: (username: string, profile: StaffProfileInput) =>
    http.put<StaffMember>(`/api/staff/${encodeURIComponent(username)}`, profile),
};
