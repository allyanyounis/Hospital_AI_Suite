/**
 * Operating theatre feature: the day board (/theatre), a case (/theatre/cases/[id]), booking (/theatre/book),
 * surgeons' rosters and leave (/theatre/surgeons) and the research insights (/theatre/insights).
 * Public API of the module: import from "@/features/theatre", never from its internal files.
 */

export { BoardView } from "./views/BoardView";
export { CaseView } from "./views/CaseView";
export { BookView } from "./views/BookView";
export { SurgeonsView } from "./views/SurgeonsView";
export { InsightsView } from "./views/InsightsView";
export { theatreApi, theatreKeys } from "./api";
export { URGENCIES, URGENCY_INFO } from "./types";
export type * from "./types";
