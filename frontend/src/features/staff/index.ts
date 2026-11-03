/**
 * Staff feature: the hospital's staff directory (/staff) and staff profiles (department, title, specialty,
 * registration number, bookable). Other features list doctors through `staffApi.doctors()`.
 * Public API of the module: import from "@/features/staff", never from its internal files.
 */

export { StaffView } from "./views/StaffView";
export { StaffProfileForm } from "./components/StaffProfileForm";
export { staffApi } from "./api";
export type * from "./types";
