import type { RouteDef } from "@/features/auth";
import { Icons } from "@/shared/ui/icons";

export const routes: RouteDef[] = [
  {
    path: "/patients",
    permission: "patients.view",
    nav: { group: "Patients", label: "Patient registry", icon: Icons.Contact, order: 0 },
  },
];
