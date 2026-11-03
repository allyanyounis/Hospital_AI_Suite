/** Thin fetch wrapper: JSON in/out, readable error messages, and a distinct error for "not signed in". */

import { env } from "@/config/env";

export class UnauthorizedError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        detail = String(body.detail[0].msg).replace(/^Value error, /, "");
      }
    } catch {
      // non-JSON error body: keep the generic message
    }
    if (res.status === 401) throw new UnauthorizedError(detail);
    throw new Error(detail);
  }
  return res.json();
}

function withBody<T>(method: "POST" | "PUT" | "PATCH", path: string, body: unknown): Promise<T> {
  return request<T>(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown = {}) => withBody<T>("POST", path, body),
  put: <T>(path: string, body: unknown) => withBody<T>("PUT", path, body),
  patch: <T>(path: string, body: unknown) => withBody<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
};

/**
 * WebSocket address for a backend path. Connects straight to the backend (the Next dev proxy does not relay
 * WebSockets); the session cookie is still sent because cookies are scoped to the host, not the port.
 */
export function wsUrl(path: string): string {
  if (env.backendWsUrl) return `${env.backendWsUrl.replace(/\/$/, "")}${path}`;
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.hostname}:${env.backendPort}${path}`;
}
