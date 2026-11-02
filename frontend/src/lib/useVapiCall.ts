"use client";

import { useEffect, useRef, useState } from "react";
import Vapi from "@vapi-ai/web";

// Public (browser-safe) VAPI identifiers, from frontend/.env.local
const VAPI_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY ?? "";
const ASSISTANT_ID = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID ?? "";
export const VAPI_CONFIGURED = Boolean(VAPI_PUBLIC_KEY && ASSISTANT_ID);

// Store Vapi on globalThis so it survives Next.js HMR (Fast Refresh).
declare global {
  var __vapiInstance: Vapi | undefined;
}
function getVapi(): Vapi {
  if (!globalThis.__vapiInstance) {
    globalThis.__vapiInstance = new Vapi(VAPI_PUBLIC_KEY);
  }
  return globalThis.__vapiInstance;
}

export type CallStatus = "idle" | "connecting" | "active";

export interface TranscriptEntry {
  role: "assistant" | "user";
  text: string;
  final: boolean;
  /** Seconds since the call started. */
  at: number;
}

// Minimal shapes of the Vapi SDK events this hook reads
interface VapiMessage {
  type?: string;
  role?: string;
  transcript?: string;
  transcriptType?: string;
}
interface VapiError {
  type?: string;
  errorMsg?: string;
  message?: unknown;
  error?: { msg?: string; errorMsg?: string; message?: unknown; error?: { type?: string } };
}

/** A VAPI voice call: status, live transcript, volume, timer and the start / end / mute controls. */
export function useVapiCall() {
  const [status, setStatus] = useState<CallStatus>("idle");
  const [assistantSpeaking, setAssistantSpeaking] = useState(false);
  const [volume, setVolume] = useState(0);
  const [muted, setMuted] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const callStartRef = useRef<number | null>(null);

  // Call timer
  useEffect(() => {
    if (status !== "active") return;
    const timer = setInterval(() => {
      if (callStartRef.current) setElapsed(Math.floor((Date.now() - callStartRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [status]);

  // Attach / detach Vapi event listeners
  useEffect(() => {
    const vapi = getVapi();
    const secondsIntoCall = () => (callStartRef.current ? Math.floor((Date.now() - callStartRef.current) / 1000) : 0);

    const resetCallState = () => {
      setStatus("idle");
      setAssistantSpeaking(false);
      setVolume(0);
      setMuted(false);
      callStartRef.current = null;
    };

    const onCallStart = () => {
      callStartRef.current = Date.now();
      setElapsed(0);
      setErrorMessage(null);
      setStatus("active");
    };

    const onMessage = (msg: VapiMessage) => {
      if (msg.type !== "transcript" || (msg.role !== "assistant" && msg.role !== "user")) return;
      const role = msg.role;
      const text = msg.transcript ?? "";
      const isFinal = msg.transcriptType === "final";
      setEntries((prev) => {
        const last = prev[prev.length - 1];
        // Replace the in-progress (partial) line of the same speaker with the newer text
        if (last && !last.final && last.role === role) {
          return [...prev.slice(0, -1), { ...last, text, final: isFinal }];
        }
        return [...prev, { role, text, final: isFinal, at: secondsIntoCall() }];
      });
    };

    const onError = (e: VapiError) => {
      // "Meeting has ended" is the normal room-closure event (e.g. assistant hung up).
      // The SDK wraps it as { type: "daily-error", error: { errorMsg, error: { type: "ejected" } } }.
      const endedMsg = e?.errorMsg || e?.error?.errorMsg || e?.error?.msg;
      if (endedMsg === "Meeting has ended" || e?.error?.error?.type === "ejected") {
        resetCallState();
        return;
      }

      console.error("Vapi Error:", e);
      let msg = "";
      if (e?.error?.message) {
        msg = typeof e.error.message === "string" ? e.error.message : JSON.stringify(e.error.message);
      } else if (e?.message) {
        msg = typeof e.message === "string" ? e.message : JSON.stringify(e.message);
      }

      if (e?.type === "start-method-error" || msg.toLowerCase().includes("credit") || msg.toLowerCase().includes("balance")) {
        setErrorMessage(msg || "Call failed to start: insufficient VAPI credits. Please recharge on dashboard.vapi.ai.");
      } else {
        setErrorMessage(msg || "Call failed to connect. Please check microphone permissions or VAPI credits.");
      }
      resetCallState();
    };

    const onSpeechStart = () => setAssistantSpeaking(true);
    const onSpeechEnd = () => setAssistantSpeaking(false);
    const onVolume = (level: number) => setVolume(level);

    vapi.on("call-start", onCallStart);
    vapi.on("call-end", resetCallState);
    vapi.on("message", onMessage);
    vapi.on("error", onError);
    vapi.on("speech-start", onSpeechStart);
    vapi.on("speech-end", onSpeechEnd);
    vapi.on("volume-level", onVolume);

    return () => {
      vapi.off("call-start", onCallStart);
      vapi.off("call-end", resetCallState);
      vapi.off("message", onMessage);
      vapi.off("error", onError);
      vapi.off("speech-start", onSpeechStart);
      vapi.off("speech-end", onSpeechEnd);
      vapi.off("volume-level", onVolume);
    };
  }, []);

  const startCall = async () => {
    if (!VAPI_CONFIGURED) {
      setErrorMessage("Set NEXT_PUBLIC_VAPI_PUBLIC_KEY and NEXT_PUBLIC_VAPI_ASSISTANT_ID in frontend/.env.local.");
      return;
    }
    setEntries([]);
    setErrorMessage(null);
    setElapsed(0);
    setStatus("connecting");
    try {
      await getVapi().start(ASSISTANT_ID);
    } catch (err) {
      console.error("Failed to start call:", err);
      setErrorMessage((err instanceof Error && err.message) || "Failed to start call. Please check your VAPI dashboard credits.");
      setStatus("idle");
    }
  };

  const endCall = () => getVapi().stop();

  const toggleMute = () => {
    const next = !muted;
    getVapi().setMuted(next);
    setMuted(next);
  };

  return { status, assistantSpeaking, volume, muted, elapsed, entries, errorMessage, startCall, endCall, toggleMute };
}
