import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  { path: "/scribe", permission: "scribe.use", title: "AI Scribe" },
  {
    path: "/scribe/session",
    permission: "scribe.use",
    nav: { group: "Clinical", label: "Live Session", icon: Icons.Mic, order: 0 },
  },
  { path: "/scribe/board", permission: "scribe.use", nav: { group: "Clinical", label: "Board", icon: Icons.Pulse, order: 1 } },
  {
    path: "/scribe/encounters",
    permission: "scribe.use",
    nav: { group: "Clinical", label: "Encounters", icon: Icons.File, order: 2 },
  },
  {
    path: "/scribe/metrics",
    permission: "scribe.use",
    nav: { group: "Hospital", label: "Pilot Metrics", icon: Icons.Chart, order: 50 },
  },
];
