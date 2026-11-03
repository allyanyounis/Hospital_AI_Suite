"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { api, wsUrl, type Appointment, type LiveEvent } from "@/lib/api";

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

/**
 * Subscribes to the backend's live events (bookings, cancellations, transcripts, schedule changes) and calls
 * `onEvent` for each. Reconnects automatically. Returns whether the connection is up.
 */
export function useLiveEvents(onEvent: (event: LiveEvent) => void): boolean {
  const [connected, setConnected] = useState(false);
  const handler = useRef(onEvent);
  useEffect(() => {
    handler.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let closed = false;

    const connect = () => {
      ws = new WebSocket(wsUrl("/api/reception/events"));
      ws.onopen = () => setConnected(true);
      ws.onmessage = (e) => {
        try {
          handler.current(JSON.parse(e.data).type as LiveEvent);
        } catch {
          // ignore malformed messages
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) retry = setTimeout(connect, 3000);
      };
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      if (!ws) return;
      // Closing mid-handshake makes the browser log an error (React mounts twice in development), so let it
      // finish opening first and close it then.
      const socket = ws;
      if (socket.readyState === WebSocket.CONNECTING) socket.onopen = () => socket.close();
      else socket.close();
    };
  }, []);

  return connected;
}

/** All appointments, reloaded whenever the voice agent books or cancels, and on demand. */
export function useAppointments() {
  const [appointments, setAppointments] = useState<Appointment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setAppointments(await api.appointments());
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load appointments");
      setAppointments((current) => current ?? []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);
  const live = useLiveEvents((event) => {
    if (event !== "schedule_updated") reload();
  });

  return { appointments, error, loading, lastUpdated, reload, live };
}
