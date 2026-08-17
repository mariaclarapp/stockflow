import { apiRequest } from "./client";

export function getDashboardSummary() {
  return apiRequest("/api/dashboard/resumo/");
}
