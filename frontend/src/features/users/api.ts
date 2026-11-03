import { http } from "@/shared/api/http";
import type { AccountChange, NewAccount, UserAccount } from "./types";

const user = (username: string) => `/api/users/${encodeURIComponent(username)}`;

export const usersApi = {
  list: () => http.get<UserAccount[]>("/api/users"),
  create: (account: NewAccount) => http.post<UserAccount>("/api/users", account),
  update: (username: string, change: AccountChange) => http.patch<UserAccount>(user(username), change),
  resetPassword: (username: string, password: string) => http.post<{ ok: boolean }>(`${user(username)}/password`, { password }),
};
