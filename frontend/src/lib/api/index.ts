/**
 * Typed client for the FastAPI backend. Each module keeps its types and calls in its own file; `api` combines them,
 * so pages import everything from "@/lib/api". A new module adds a file here and one line to `api`.
 */

import { receptionApi } from "./reception";
import { scheduleApi } from "./schedule";
import { scribeApi } from "./scribe";
import { sessionApi } from "./session";

export { UnauthorizedError, wsUrl } from "./client";
export * from "./reception";
export * from "./schedule";
export * from "./scribe";
export * from "./session";

export const api = { ...sessionApi, ...scheduleApi, ...receptionApi, ...scribeApi };
