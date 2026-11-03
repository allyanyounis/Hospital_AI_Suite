/**
 * Which cached queries each live event makes stale. Query keys start with the feature name, so one prefix
 * refetches every list and detail of that feature that is on screen (and marks the rest stale).
 * Add an entry here when the backend starts broadcasting a new event type.
 */

import type { QueryKey } from "@tanstack/react-query";

export const LIVE_INVALIDATIONS: Record<string, QueryKey[]> = {
  theatre_updated: [["theatre"], ["clinical"]],
  appointment_booked: [["appointments"]],
  appointment_canceled: [["appointments"]],
  transcript_saved: [["appointments"]],
};
