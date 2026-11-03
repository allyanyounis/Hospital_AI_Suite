"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

const noSubscription = () => () => {};

/** False during server render and hydration; true once mounted (charts need a measured container). */
export function useMounted(): boolean {
  return useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
}

/** The current time, refreshed every `intervalMs`. */
export function useNow(intervalMs = 60_000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return now;
}
