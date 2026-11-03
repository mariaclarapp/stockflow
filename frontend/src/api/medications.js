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
  competenceId = "",
  upsId = "",
  unit = "",
  stockStatus = "",
  validationStatus = "",
  ordering = "descricao",
} = {}) {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  if (subgroupId) query.set("subgrupo", subgroupId);
  if (classificationId) query.set("classificacao", classificationId);
  if (uncategorized) query.set("sem_categoria", "true");
  if (ids.length) query.set("ids", ids.join(","));
  if (competenceId) query.set("competencia", competenceId);
  if (upsId) query.set("ups", upsId);
  if (unit) query.set("unidade", unit);
  if (stockStatus) query.set("situacao", stockStatus);
  if (validationStatus) query.set("validacao", validationStatus);
  if (ordering) query.set("ordenacao", ordering);
  query.set("contrato_estoque", "2");

  const suffix = query.size ? `?${query.toString()}` : "";
  const data = ensureList(
    await apiRequest(`/api/medicamentos/${suffix}`, { cache: "no-store" }),
  );
  if (
    data.length
    && (
      !Object.hasOwn(data[0], "estoque_por_ups")
      || !Object.hasOwn(data[0], "situacao_estoque")
      || !Object.hasOwn(data[0], "situacao_validacao")
    )
  ) {
    throw new ApiError(
      "O backend está executando uma versão anterior. Reinicie o servidor da API para carregar os saldos por UPS.",
      200,
    );
  }
  return data;
}

export async function getMedicationOptions() {
  let data;
  try {
    data = ensureObject(
      await apiRequest("/api/medicamentos/opcoes/?contrato_estoque=2", {
        cache: "no-store",
      }),
    );
  } catch (error) {
    const [competencias, ups] = await Promise.all([
      apiRequest("/api/competencias/"),
      apiRequest("/api/ups/"),
    ]);
    data = {
      competencia_padrao_id: competencias[0]?.id || null,
      competencias,
      ups: ups.filter((item) => item.participa_competencia),
      unidades: [],
    };
    if (!data.competencias.length && !data.ups.length) throw error;
  }
  if (
    !Array.isArray(data.competencias)
    || !Array.isArray(data.ups)
    || !Array.isArray(data.unidades)
  ) {
    throw new ApiError("A API retornou uma resposta inesperada.", 200);
  }
  return data;
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
