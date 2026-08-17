import { ApiError, apiRequest } from "./client";

function ensureList(data) {
  if (!Array.isArray(data)) {
    throw new ApiError("A API retornou uma resposta inesperada.", 200);
  }
  return data;
}

function ensureObject(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new ApiError("A API retornou uma resposta inesperada.", 200);
  }
  return data;
}

export async function getMedications({ search = "", subgroupId = "" } = {}) {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  if (subgroupId) query.set("subgrupo", subgroupId);

  const suffix = query.size ? `?${query.toString()}` : "";
  return ensureList(await apiRequest(`/api/medicamentos/${suffix}`));
}

export async function getMedicationSubgroups() {
  return ensureList(await apiRequest("/api/subgrupos-gmus/"));
}

export async function getMedication(id) {
  return ensureObject(await apiRequest(`/api/medicamentos/${id}/`));
}

export async function getMedicationHistory(id) {
  const data = ensureObject(
    await apiRequest(`/api/medicamentos/${id}/historico/`),
  );
  if (!Array.isArray(data.historico)) {
    throw new ApiError("A API retornou uma resposta inesperada.", 200);
  }
  return data;
}

export async function getMedicationDetail(id) {
  const [medication, history] = await Promise.all([
    getMedication(id),
    getMedicationHistory(id),
  ]);
  return { medication, history };
}
