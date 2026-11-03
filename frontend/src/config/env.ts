/**
 * Browser-visible settings, read from frontend/.env.local (see .env.example). This is the only file that reads
 * process.env.NEXT_PUBLIC_*; Next.js inlines these at build time, so each must be read by its literal name.
 * (BACKEND_URL, the proxy target for /api/*, is server-only and read in next.config.ts.)
 */
export const env = {
  /** VAPI public (browser-safe) key and assistant id for the voice agent; both empty = voice agent disabled */
  vapiPublicKey: process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY ?? "",
  vapiAssistantId: process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID ?? "",
  /** Full WebSocket base, e.g. wss://api.example.org; empty = same host as the page, on `backendPort` */
  backendWsUrl: process.env.NEXT_PUBLIC_BACKEND_WS_URL ?? "",
  backendPort: process.env.NEXT_PUBLIC_BACKEND_PORT || "8000",
} as const;
