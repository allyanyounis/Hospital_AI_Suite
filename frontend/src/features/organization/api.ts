import { http } from "@/shared/api/http";
import type { Department, DepartmentChange, NewDepartment } from "./types";

export const departmentsApi = {
  list: () => http.get<Department[]>("/api/departments"),
  create: (department: NewDepartment) => http.post<Department>("/api/departments", department),
  update: (id: number, change: DepartmentChange) => http.patch<Department>(`/api/departments/${id}`, change),
};
