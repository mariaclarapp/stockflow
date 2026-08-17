import { apiRequest } from "./client";

export function getCompetenciesTracking() {
  return apiRequest("/api/competencias/acompanhamento/");
}
