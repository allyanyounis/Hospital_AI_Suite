import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  {
    path: "/reception/agent",
    permission: "voice_agent.use",
    nav: { group: "Front desk", label: "Voice Agent", icon: Icons.Bot, order: 0 },
  },
  {
    path: "/reception/monitoring",
    permission: "call_costs.view",
    nav: { group: "Hospital", label: "Call Costs", icon: Icons.Activity, order: 60 },
  },
];
