/** Sign-in and app configuration. */

import { http } from "./client";

export type User = { username: string; display_name: string; role: "clinician" | "admin" };

export type AppConfig = {
  environment_banner: string;
  retention_days: number;
  clinic_timezone: string;
  transcriber: string;
  transcriber_ready: boolean;
  note_model: string;
  notes_ready: boolean;
};

export const sessionApi = {
  config: () => http.get<AppConfig>("/api/config"),
  session: () => http.get<{ user: User | null }>("/api/session"),
  login: (username: string, password: string) => http.post<User>("/api/login", { username, password }),
  logout: () => http.post<{ ok: boolean }>("/api/logout"),
};
