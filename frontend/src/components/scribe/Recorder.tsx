"use client";

import { useEffect, useRef, useState } from "react";
import { Headphones, Mic, Pause, Play, Trash2 } from "lucide-react";
import { api, wsUrl, type Encounter, type LiveMessage, type Segment } from "@/lib/api";
import { formatDuration as formatTime } from "@/lib/format";

export type RecorderState = "idle" | "recording" | "paused";
type LiveStatus = "connecting" | "live" | "unavailable";

const BAR_COUNT = 9;
const CHUNK_MS = 250;
const READY_TIMEOUT_MS = 6000;
const FINALIZE_TIMEOUT_MS = 20000;

function pickMimeType(): string | undefined {
  // Chrome/Firefox record webm/opus; Safari records mp4. Both are accepted by the transcriber.
  for (const type of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) return type;
  }
  return undefined;
}

/** Opens the live transcription socket; resolves once the backend has connected to the provider, or null. */
function openLiveSocket(): Promise<WebSocket | null> {
  return new Promise((resolve) => {
    let settled = false;
    const done = (ws: WebSocket | null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(ws);
    };
    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl("/api/encounters/live"));
    } catch {
      resolve(null);
      return;
    }
    const timer = setTimeout(() => {
      ws.close();
      done(null);
    }, READY_TIMEOUT_MS);
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as LiveMessage;
        if (msg.type === "ready") done(ws);
        else if (msg.type === "error") done(null);
      } catch {}
    };
    ws.onerror = () => done(null);
    ws.onclose = () => done(null);
  });
}

export function Recorder({
  disabled,
  onComplete,
  onStateChange,
}: {
  disabled: boolean;
  /** Called on Stop with the encounter: from the live stream, or by uploading the recording as a fallback. */
  onComplete: (encounter: Promise<Encounter>) => void;
  onStateChange?: (state: RecorderState) => void;
}) {
  const [state, setState] = useState<RecorderState>("idle");
  const [starting, setStarting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [levels, setLevels] = useState<number[]>(() => Array(BAR_COUNT).fill(0.15));
  const [error, setError] = useState<string | null>(null);
  const [liveStatus, setLiveStatus] = useState<LiveStatus>("connecting");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [interim, setInterim] = useState<{ text: string; speaker: number | null }>({ text: "", speaker: null });

  const recorderRef = useRef<MediaRecorder | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const finalizeRef = useRef<((e: Encounter | null) => void) | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<number | null>(null);
  const discardRef = useRef(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  // Elapsed time is accumulated across pauses: banked seconds + time since the last resume.
  const bankedRef = useRef(0);
  const resumedAtRef = useRef(0);

  function changeState(next: RecorderState) {
    setState(next);
    onStateChange?.(next);
  }

  function stopTimer() {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  }

  function startTimer() {
    resumedAtRef.current = Date.now();
    timerRef.current = setInterval(() => setElapsed(bankedRef.current + (Date.now() - resumedAtRef.current) / 1000), 250);
  }

  function teardownAudio() {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null;
  }

  function closeSocket() {
    const ws = socketRef.current;
    socketRef.current = null;
    if (ws && ws.readyState <= WebSocket.OPEN) ws.close();
  }

  useEffect(() => {
    return () => {
      stopTimer();
      teardownAudio();
      closeSocket();
      const rec = recorderRef.current;
      if (rec) {
        discardRef.current = true;
        rec.stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  // Keep the newest words in view
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [segments, interim]);

  function startWaveform(stream: MediaStream) {
    try {
      const ctx = new AudioContext();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      ctx.createMediaStreamSource(stream).connect(analyser);
      audioCtxRef.current = ctx;
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        // Use the lower bins, where speech energy sits.
        setLevels(Array.from({ length: BAR_COUNT }, (_, i) => Math.max(0.15, Math.min(1, (data[i + 1] / 255) * 1.4))));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      // Waveform is decorative; recording still works without it.
    }
  }

  function attachLiveHandlers(ws: WebSocket) {
    ws.onmessage = (e) => {
      let msg: LiveMessage;
      try {
        msg = JSON.parse(e.data);
      } catch {
        return;
      }
      switch (msg.type) {
        case "segment":
          setSegments((prev) => {
            const next = prev.filter((s) => s.id !== msg.segment.id);
            next.push(msg.segment);
            return next.sort((a, b) => a.id - b.id);
          });
          break;
        case "interim":
          setInterim({ text: msg.text, speaker: msg.speaker });
          break;
        case "encounter":
          finalizeRef.current?.(msg.encounter);
          break;
        case "empty":
          finalizeRef.current?.(null);
          break;
        case "error":
          setLiveStatus("unavailable");
          finalizeRef.current?.(null);
          break;
      }
    };
    ws.onclose = () => {
      if (socketRef.current === ws) {
        socketRef.current = null;
        setLiveStatus("unavailable");
      }
      finalizeRef.current?.(null);
    };
  }

  /** After Stop: ask the backend to finish the live transcript; resolves null if it can't. */
  function finalizeLive(ws: WebSocket): Promise<Encounter | null> {
    return new Promise((resolve) => {
      const timer = setTimeout(() => finish(null), FINALIZE_TIMEOUT_MS);
      const finish = (e: Encounter | null) => {
        clearTimeout(timer);
        finalizeRef.current = null;
        resolve(e);
      };
      finalizeRef.current = finish;
      ws.send(JSON.stringify({ type: "stop" }));
    });
  }

  async function start() {
    setError(null);
    setStarting(true);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Microphone access was blocked. Allow it in the browser and try again.");
      setStarting(false);
      return;
    }

    // Connect before recording starts so the provider receives the audio header in the first chunk.
    setSegments([]);
    setInterim({ text: "", speaker: null });
    setLiveStatus("connecting");
    const ws = await openLiveSocket();
    socketRef.current = ws;
    if (ws) {
      attachLiveHandlers(ws);
      setLiveStatus("live");
    } else {
      setLiveStatus("unavailable");
    }

    const mimeType = pickMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const chunks: Blob[] = [];
    discardRef.current = false;
    recorder.ondataavailable = (e) => {
      if (!e.data.size) return;
      chunks.push(e.data); // kept for the upload fallback
      const live = socketRef.current;
      if (live?.readyState === WebSocket.OPEN) live.send(e.data);
    };
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const live = socketRef.current;
      if (discardRef.current) {
        if (live?.readyState === WebSocket.OPEN) live.send(JSON.stringify({ type: "discard" }));
        closeSocket();
        return;
      }
      const audio = new Blob(chunks, { type: recorder.mimeType });
      const upload = () => api.startFromRecording(audio);
      if (live?.readyState === WebSocket.OPEN) {
        onComplete(
          finalizeLive(live).then((encounter) => {
            closeSocket();
            return encounter ?? upload();
          }),
        );
      } else {
        closeSocket();
        onComplete(upload());
      }
    };
    recorder.start(CHUNK_MS);
    recorderRef.current = recorder;
    bankedRef.current = 0;
    setElapsed(0);
    startTimer();
    startWaveform(stream);
    setStarting(false);
    changeState("recording");
  }

  function togglePause() {
    const rec = recorderRef.current;
    if (!rec) return;
    if (state === "recording") {
      rec.pause();
      stopTimer();
      bankedRef.current += (Date.now() - resumedAtRef.current) / 1000;
      setElapsed(bankedRef.current);
      audioCtxRef.current?.suspend().catch(() => {});
      setLevels(Array(BAR_COUNT).fill(0.15));
      changeState("paused");
    } else if (state === "paused") {
      rec.resume();
      startTimer();
      audioCtxRef.current?.resume().catch(() => {});
      changeState("recording");
    }
  }

  function stop(discard: boolean) {
    if (discard && !window.confirm("Discard this recording? Nothing will be saved.")) return;
    discardRef.current = discard;
    stopTimer();
    teardownAudio();
    recorderRef.current?.stop();
    recorderRef.current = null;
    setLevels(Array(BAR_COUNT).fill(0.15));
    changeState("idle");
  }

  if (state === "idle") {
    return (
      <div className="flex items-center gap-4">
        <button
          onClick={start}
          disabled={disabled || starting}
          className="flex items-center gap-2 rounded-full bg-brand-700 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {starting ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
          ) : (
            <Mic className="h-4 w-4" />
          )}
          {starting ? "Connecting…" : "Start recording"}
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    );
  }

  const paused = state === "paused";
  const speakerCount = new Set(segments.map((s) => s.speaker)).size;
  const live = liveStatus === "live";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-xl font-semibold text-slate-900">Live Transcript</h3>
          <p className="mt-0.5 text-sm text-slate-500">
            {paused
              ? "Recording paused"
              : live
                ? "Audio transcribing activated"
                : "Recording · transcript will appear when you stop"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {live && (
            <span className="flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-800">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-600" />
              {speakerCount} speaker{speakerCount === 1 ? "" : "s"} detected
            </span>
          )}
          <button
            onClick={() => stop(true)}
            title="Discard recording"
            aria-label="Discard recording"
            className="flex h-8 w-8 items-center justify-center rounded-full border border-red-200 bg-red-50 text-red-600 hover:bg-red-100"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Listening card */}
      <div className="flex items-center gap-4 rounded-xl border border-brand-200 bg-brand-50/60 px-5 py-4">
        <div className="relative flex h-12 w-12 shrink-0 items-center justify-center">
          {!paused && <span className="absolute inset-0 animate-ping rounded-full bg-brand-300/40" />}
          <span className="relative flex h-12 w-12 items-center justify-center rounded-full bg-brand-700 text-white shadow">
            <Headphones className="h-5 w-5" />
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-brand-800">
            {paused ? "Paused — not listening" : "Listening to the conversation"}
          </p>
          <div className="mt-2 flex h-6 items-center gap-1" aria-hidden>
            {levels.map((l, i) => (
              <span
                key={i}
                className={`w-1 rounded-full transition-[height] duration-75 ${paused ? "bg-slate-300" : "bg-brand-600"}`}
                style={{ height: `${Math.round(l * 24)}px` }}
              />
            ))}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${
              paused ? "border-amber-200 bg-amber-50 text-amber-700" : "border-red-200 bg-red-50 text-red-600"
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${paused ? "bg-amber-500" : "animate-pulse bg-red-600"}`} />
            {paused ? "PAUSED" : "REC"}
          </span>
          <span className="text-sm font-medium tabular-nums text-slate-600">{formatTime(elapsed)}</span>
        </div>
      </div>

      {/* Live transcript */}
      <div ref={scrollRef} className="my-4 min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {!live && (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-400">
            Live view isn&apos;t available right now. The recording will be transcribed when you press Stop.
          </div>
        )}
        {live && segments.length === 0 && !interim.text && (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-400">
            Start speaking — words will appear here as they are said.
          </div>
        )}
        {segments.map((s) => (
          <LiveLine key={s.id} speaker={s.speaker} time={s.start} text={s.text} />
        ))}
        {live && interim.text && <LiveLine speaker={interim.speaker} text={interim.text} interim />}
      </div>

      {/* Controls */}
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={togglePause}
          className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 py-3 text-sm font-semibold text-brand-800 hover:bg-slate-100"
        >
          {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
          {paused ? "Resume" : "Pause"}
        </button>
        <button
          onClick={() => stop(false)}
          className="flex items-center justify-center gap-2 rounded-xl border border-red-200 bg-red-50 py-3 text-sm font-semibold text-red-600 hover:bg-red-100"
        >
          <span className="h-3 w-3 rounded-sm bg-red-600" />
          Stop Recording
        </button>
      </div>
    </div>
  );
}

function LiveLine({ speaker, time, text, interim }: { speaker: number | null; time?: number; text: string; interim?: boolean }) {
  const label = speaker === null ? "Speaking…" : `Speaker ${speaker + 1}`;
  const initials = speaker === null ? "…" : `S${speaker + 1}`;
  const tone = speaker === null || speaker % 2 === 0 ? "border-brand-200 text-brand-700" : "border-slate-300 text-slate-600";
  return (
    <div className="flex gap-3">
      <span
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border bg-white text-xs font-bold ${tone}`}
      >
        {initials}
      </span>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-800">{label}</span>
          {time !== undefined && <span className="tabular-nums text-slate-400">{formatTime(time)}</span>}
        </div>
        <p
          className={`rounded-xl border px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
            interim
              ? "border-dashed border-slate-200 bg-slate-50 italic text-slate-500"
              : "border-slate-200 bg-white text-slate-800"
          }`}
        >
          {text}
        </p>
      </div>
    </div>
  );
}
