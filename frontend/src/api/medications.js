import { ApiError, apiRequest } from "./client";
import { getCsrfToken } from "./csrf";

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

export async function getMedications({
  search = "",
  subgroupId = "",
  classificationId = "",
  uncategorized = false,
  ids = [],
} = {}) {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  if (subgroupId) query.set("subgrupo", subgroupId);
  if (classificationId) query.set("classificacao", classificationId);
  if (uncategorized) query.set("sem_categoria", "true");
  if (ids.length) query.set("ids", ids.join(","));

  const suffix = query.size ? `?${query.toString()}` : "";
  return ensureList(await apiRequest(`/api/medicamentos/${suffix}`));
}

export async function getMedicationComparison(ids) {
  const query = new URLSearchParams({ ids: ids.join(",") });
  const data = ensureObject(
    await apiRequest(`/api/medicamentos/comparacao/?${query.toString()}`),
  );
  if (!Array.isArray(data.ups) || !Array.isArray(data.medicamentos)) {
    throw new ApiError("A API retornou uma resposta inesperada.", 200);
  }
  return data;
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

async function classificationRequest(path, method, body) {
  const csrfToken = await getCsrfToken();
  return apiRequest(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export async function getClassifications() {
  return ensureList(await apiRequest("/api/classificacoes/"));
}

export async function createClassification(data) {
  return ensureObject(
    await classificationRequest("/api/classificacoes/", "POST", data),
  );
}

export async function updateClassification(id, data) {
  return ensureObject(
    await classificationRequest(`/api/classificacoes/${id}/`, "PATCH", data),
  );
}

export async function deleteClassification(id) {
  await classificationRequest(`/api/classificacoes/${id}/`, "DELETE");
}

export async function associateMedicationClassification(medicationId, classificationId) {
  return ensureObject(
    await classificationRequest(
      `/api/medicamentos/${medicationId}/classificacoes/`,
      "POST",
      { classificacao_id: classificationId },
    ),
  );
}

export async function removeMedicationClassification(medicationId, classificationId) {
  await classificationRequest(
    `/api/medicamentos/${medicationId}/classificacoes/${classificationId}/`,
    "DELETE",
  );
}

export async function classifyMedications(ids, classificationId) {
  return ensureObject(
    await classificationRequest(
      "/api/medicamentos/classificacoes/lote/",
      "POST",
      {
        medicamento_ids: ids,
        classificacao_id: classificationId,
      },
    ),
  );
}

export async function unclassifyMedications(ids, classificationId) {
  return ensureObject(
    await classificationRequest(
      "/api/medicamentos/classificacoes/lote/remover/",
      "POST",
      {
        medicamento_ids: ids,
        classificacao_id: classificationId,
      },
    ),
  );
}
