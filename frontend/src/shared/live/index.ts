/** App-wide live events: one WebSocket to /api/events, query invalidation by event type, and subscriber hooks. */

export { LiveEventsProvider, useLiveConnected, useLiveEvent, type LiveMessage } from "./LiveEventsProvider";
export { LIVE_INVALIDATIONS } from "./invalidation";
