/**
 * Organisation feature: the hospital's departments (admin page /admin/departments). Other features read the
 * department list through `departmentsApi`.
 * Public API of the module: import from "@/features/organization", never from its internal files.
 */

export { DepartmentsView } from "./views/DepartmentsView";
export { departmentsApi } from "./api";
export { DEPARTMENT_KINDS } from "./types";
export type * from "./types";
