"use client";

import { useEffect, useRef } from "react";
import { Phone, PhoneOff, Mic, MicOff, Bot, AlertCircle, Loader2 } from "lucide-react";
import { CallStatus, useVapiCall } from "../useVapiCall";

export type { CallStatus };

const SPEAKERS = {
  assistant: { tag: "S1", label: "Agent · Steven Smith" },
  user: { tag: "S2", label: "Patient" },
} as const;

// Relative heights for the waveform bars (tallest in the middle)
const BAR_SHAPE = [0.35, 0.5, 0.65, 0.8, 0.95, 1, 0.95, 0.8, 0.65, 0.5, 0.35];

const formatClock = (seconds: number) =>
  `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

export function VoiceAgent({ onStatusChange }: { onStatusChange?: (status: CallStatus) => void }) {
  const { status, assistantSpeaking, volume, muted, elapsed, entries, errorMessage, startCall, endCall, toggleMute } =
    useVapiCall();
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Let the page reflect call state (e.g. the Agent Status card)
  useEffect(() => {
    onStatusChange?.(status);
  }, [status, onStatusChange]);

  // Auto-scroll to newest line
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [entries]);

  const isActive = status === "active";
  const headline =
    status === "connecting"
      ? "Connecting..."
      : !isActive
        ? "Ready to take calls"
        : assistantSpeaking
          ? "AI Speaking..."
          : "Listening...";
  const subline =
    status === "connecting"
      ? "Setting up the voice line"
      : isActive
        ? `Call in progress · ${formatClock(elapsed)}`
        : "Press the call button to talk to Steven";

  return (
    <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
      {/* Call stage */}
      <div className="xl:col-span-3 relative overflow-hidden rounded-2xl border border-slate-200/80 shadow-sm bg-gradient-to-br from-brand-50 via-white to-white px-6 py-10 flex flex-col items-center justify-center min-h-[460px]">
        {errorMessage && (
          <div className="absolute top-4 left-4 right-4 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block">Connection Error</span>
              <span>{errorMessage}</span>
            </div>
          </div>
        )}

        {/* Orb */}
        <div className="relative flex items-center justify-center w-48 h-48">
          {isActive && (
            <>
              <span className="absolute inset-0 rounded-full bg-brand-700/10 animate-ping" style={{ animationDuration: "2s" }} />
              <span
                className="absolute rounded-full border-2 border-brand-700/30 transition-all duration-150"
                style={{ inset: `${12 - volume * 12}px` }}
              />
            </>
          )}
          <span className="absolute inset-6 rounded-full border border-brand-700/20" />
          <div
            className={`relative w-28 h-28 rounded-full flex items-center justify-center shadow-lg transition-all duration-300 ${
              isActive ? "bg-brand-700 text-white" : "bg-brand-100 text-brand-700"
            }`}
          >
            {status === "connecting" ? <Loader2 className="w-12 h-12 animate-spin" /> : <Bot className="w-12 h-12" />}
          </div>
        </div>

        <h3 className="mt-6 text-2xl font-bold text-slate-800">{headline}</h3>
        <p className="mt-1 text-sm text-slate-500">{subline}</p>

        {/* Waveform */}
        <div className="mt-6 h-16 flex items-end gap-1.5" aria-hidden>
          {BAR_SHAPE.map((shape, i) => {
            const level = isActive ? (assistantSpeaking ? Math.max(volume, 0.15) : 0.08) : 0.05;
            return (
              <span
                key={i}
                className={`w-2 rounded-full transition-all duration-150 ${isActive ? "bg-brand-700" : "bg-slate-300"}`}
                style={{ height: `${Math.max(6, shape * level * 64 + (assistantSpeaking ? (i % 3) * 3 : 0))}px` }}
              />
            );
          })}
        </div>

        {/* Controls */}
        <div className="mt-8 flex items-center gap-5">
          {isActive && (
            <button
              onClick={toggleMute}
              title={muted ? "Unmute microphone" : "Mute microphone"}
              className={`w-14 h-14 rounded-full flex items-center justify-center border shadow-sm transition-colors ${
                muted ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {muted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
          )}

          {status === "idle" ? (
            <button
              onClick={startCall}
              title="Start call"
              className="px-8 h-16 rounded-full bg-brand-700 hover:bg-brand-800 text-white font-semibold shadow-lg flex items-center gap-3 transition-all active:scale-95"
            >
              <Phone className="w-6 h-6" />
              Call AI Receptionist
            </button>
          ) : (
            <button
              onClick={endCall}
              title="End call"
              className="w-16 h-16 rounded-full bg-red-600 hover:bg-red-700 text-white shadow-lg flex items-center justify-center transition-all active:scale-95"
            >
              <PhoneOff className="w-6 h-6" />
            </button>
          )}
        </div>
        {muted && isActive && <p className="mt-3 text-xs text-slate-500">Your microphone is muted</p>}
      </div>

      {/* Live transcript */}
      <div className="xl:col-span-2 bg-white rounded-2xl border border-slate-200/80 shadow-sm flex flex-col min-h-[460px] max-h-[600px]">
        <div className="px-5 py-4 border-b border-slate-200/80 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-800">Live Transcript</h3>
            <p className="text-xs text-slate-400">
              <span className="font-semibold text-brand-700">S1</span> Agent ·{" "}
              <span className="font-semibold text-slate-600">S2</span> Patient
            </p>
          </div>
          {isActive && (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-red-600">
              <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" /> LIVE
            </span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 text-sm">
          {entries.length === 0 ? (
            <p className="text-slate-400 text-center italic mt-24">
              {isActive ? "Listening... speak into your microphone." : "The conversation will appear here during the call."}
            </p>
          ) : (
            entries.map((entry, idx) => {
              const speaker = SPEAKERS[entry.role];
              const isAgent = entry.role === "assistant";
              return (
                <div key={idx} className="flex gap-3">
                  <span
                    className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center text-xs font-bold ${
                      isAgent ? "bg-brand-700 text-white" : "bg-slate-200 text-slate-700"
                    }`}
                  >
                    {speaker.tag}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-slate-400 mb-0.5">
                      <span className={`font-semibold ${isAgent ? "text-brand-700" : "text-slate-600"}`}>{speaker.label}</span>
                      {" · "}
                      {formatClock(entry.at)}
                    </p>
                    <p className={`text-slate-800 leading-relaxed ${entry.final ? "" : "text-slate-400 italic"}`}>{entry.text}</p>
                  </div>
                </div>
              );
            })
          )}
          <div ref={transcriptEndRef} />
        </div>
      </div>
    </div>
  );
}
