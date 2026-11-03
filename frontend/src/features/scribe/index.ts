/**
 * AI medical scribe feature: live session, board, encounters (note, codes, tasks, letters) and pilot metrics.
 * Public API of the module: import from "@/features/scribe", never from its internal files.
 */

export { BoardView } from "./views/BoardView";
export { EncountersView } from "./views/EncountersView";
export { MetricsView } from "./views/MetricsView";
export { SessionView } from "./views/SessionView";
export { StatusPill } from "./components/status";
export { scribeApi } from "./api";
export type * from "./types";
