import { http } from "@/shared/api/http";
import type { PortalAppointment, PortalProfile } from "./types";

export const portalApi = {
  me: () => http.get<PortalProfile>("/api/portal/me"),
  appointments: () => http.get<PortalAppointment[]>("/api/portal/appointments"),
};
