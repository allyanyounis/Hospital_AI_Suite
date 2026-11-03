import { http } from "@/shared/api/http";
import type { AppConfig, User } from "./types";

export const authApi = {
  config: () => http.get<AppConfig>("/api/config"),
  me: () => http.get<User>("/api/me"),
  /** The signed-in user or null; never 401, so checking on page load stays quiet */
  session: () => http.get<{ user: User | null }>("/api/session"),
  login: (username: string, password: string) => http.post<User>("/api/login", { username, password }),
  logout: () => http.post<{ ok: boolean }>("/api/logout"),
  changePassword: (currentPassword: string, newPassword: string) =>
    http.post<{ ok: boolean }>("/api/me/password", { current_password: currentPassword, new_password: newPassword }),
};
