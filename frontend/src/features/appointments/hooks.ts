"use client";

import { useCallback, useEffect, useState } from "react";
import { useLiveConnected, useLiveEvent } from "@/shared/live";
import { appointmentsApi } from "./api";
import type { Appointment, LiveEvent } from "./types";

const LIVE_EVENT_TYPES: LiveEvent[] = ["appointment_booked", "appointment_canceled", "transcript_saved", "schedule_updated"];

/**
 * Subscribes to the backend's live events (bookings, cancellations, transcripts, schedule changes) and calls
 * `onEvent` for each. Uses the app-wide connection (shared/live), which reconnects automatically. Returns whether
 * the connection is up. Pass `enabled = false` when the user may not see these events (nothing is delivered).
 */
export function useLiveEvents(onEvent: (event: LiveEvent) => void, enabled = true): boolean {
  const connected = useLiveConnected();
  useLiveEvent(LIVE_EVENT_TYPES, (message) => {
    if (enabled) onEvent(message.type as LiveEvent);
  });
  return enabled && connected;
}

/**
 * All appointments, reloaded whenever anyone books or cancels (front desk, voice agent, portal), and on demand.
 * With `enabled = false` (user lacks appointments.view) nothing is fetched and `appointments` is an empty list.
 */
export function useAppointments(enabled = true) {
  const [appointments, setAppointments] = useState<Appointment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setAppointments(await appointmentsApi.list());
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
    if (enabled) reload();
  }, [reload, enabled]);
  const live = useLiveEvents((event) => {
    if (event !== "schedule_updated") reload();
  }, enabled);

  return { appointments: enabled ? appointments : [], error, loading, lastUpdated, reload, live };
}
