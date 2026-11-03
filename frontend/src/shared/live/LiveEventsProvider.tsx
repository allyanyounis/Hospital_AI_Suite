"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { wsUrl } from "@/shared/api/http";
import { LIVE_INVALIDATIONS } from "./invalidation";

/** One message from /api/events: always a `type`, plus whatever payload that event carries (e.g. `day`). */
export type LiveMessage = { type: string; [field: string]: unknown };
type Listener = (message: LiveMessage) => void;

type LiveEvents = {
  connected: boolean;
  /** Adds a listener; returns the function that removes it. */
  subscribe: (listener: Listener) => () => void;
};

const LiveEventsContext = createContext<LiveEvents | null>(null);

/**
 * The app's single connection to the backend's live events (/api/events). Every message invalidates the queries
 * listed in LIVE_INVALIDATIONS and is handed to each useLiveEvent subscriber. Reconnects 3s after a drop; after a
 * reconnect all mapped queries are invalidated, since events may have been missed meanwhile. With
 * `enabled = false` (the user lacks appointments.view, which the socket requires) no connection is opened.
 */
export function LiveEventsProvider({ enabled, children }: { enabled: boolean; children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);
  const [listeners] = useState(() => new Set<Listener>());
  const [subscribe] = useState(() => (listener: Listener) => {
    listeners.add(listener);
    return () => void listeners.delete(listener);
  });
  const value = useMemo(() => ({ connected, subscribe }), [connected, subscribe]);

  useEffect(() => {
    if (!enabled) return;
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let closed = false;
    let wasOpen = false;

    const invalidate = (keys: readonly (readonly unknown[])[] | undefined) =>
      keys?.forEach((queryKey) => queryClient.invalidateQueries({ queryKey }));

    const connect = () => {
      ws = new WebSocket(wsUrl("/api/events"));
      ws.onopen = () => {
        setConnected(true);
        if (wasOpen) invalidate(Object.values(LIVE_INVALIDATIONS).flat());
        wasOpen = true;
      };
      ws.onmessage = (e) => {
        let message: LiveMessage;
        try {
          message = JSON.parse(e.data);
          if (typeof message?.type !== "string") return;
        } catch {
          return; // ignore malformed messages
        }
        invalidate(LIVE_INVALIDATIONS[message.type]);
        listeners.forEach((listener) => listener(message));
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
      setConnected(false);
      if (!ws) return;
      // Closing mid-handshake makes the browser log an error (React mounts twice in development), so let it
      // finish opening first and close it then.
      const socket = ws;
      if (socket.readyState === WebSocket.CONNECTING) socket.onopen = () => socket.close();
      else socket.close();
    };
  }, [enabled, queryClient, listeners]);

  return <LiveEventsContext.Provider value={value}>{children}</LiveEventsContext.Provider>;
}

/**
 * Calls `handler` for each live event whose type is `types` (or one of them; "*" = every event). The handler may
 * change between renders without resubscribing. Outside a LiveEventsProvider this does nothing.
 */
export function useLiveEvent(types: string | readonly string[], handler: (message: LiveMessage) => void): void {
  const live = useContext(LiveEventsContext);
  const subscribe = live?.subscribe;
  const current = useRef(handler);
  useEffect(() => {
    current.current = handler;
  }, [handler]);

  const wanted = (typeof types === "string" ? [types] : [...types]).sort().join(",");
  useEffect(() => {
    if (!subscribe) return;
    const set = new Set(wanted.split(","));
    return subscribe((message) => {
      if (set.has("*") || set.has(message.type)) current.current(message);
    });
  }, [subscribe, wanted]);
}

/** Whether the live-events connection is currently up (false when disabled or outside the provider). */
export function useLiveConnected(): boolean {
  return useContext(LiveEventsContext)?.connected ?? false;
}
