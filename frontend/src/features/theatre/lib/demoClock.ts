"use client";

/**
 * The admin demo clock: replay today's lists at another time of day (minutes after midnight), or null for real
 * time. Kept for the browser session and shared by every theatre page; the backend honours it for admins only.
 */

import { useSyncExternalStore } from "react";

const KEY = "theatre.demoClock";
const listeners = new Set<() => void>();

function read(): number | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(KEY);
  return raw == null ? null : Number(raw);
}

export function setDemoClock(minutes: number | null) {
  if (minutes == null) window.sessionStorage.removeItem(KEY);
  else window.sessionStorage.setItem(KEY, String(Math.round(minutes)));
  listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useDemoClock(): number | null {
  return useSyncExternalStore(subscribe, read, () => null);
}
