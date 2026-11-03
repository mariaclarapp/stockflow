import { apiRequest } from "./client";
import { getCsrfToken } from "./csrf";

export async function uploadStock(file, { reimportar = false } = {}) {
  return uploadReport("estoque", file, { reimportar });
}

export async function uploadMovement(file, { reimportar = false } = {}) {
  return uploadReport("movimentacoes", file, { reimportar });
}

export async function deleteImport(importacaoId) {
  const csrfToken = await getCsrfToken();
  return apiRequest(`/api/importacoes/${importacaoId}/`, {
    method: "DELETE",
    headers: { "X-CSRFToken": csrfToken, "Content-Type": "application/json" },
    body: JSON.stringify({ confirmar: true }),
  });
}

export async function previewImport(file) {
  const csrfToken = await getCsrfToken();
  const formData = new FormData();
  formData.append("arquivo", file);
  return apiRequest("/api/importacoes/previsualizar/", {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken },
    body: formData,
  });
}

export function getImports() {
  return apiRequest("/api/importacoes/");
}

export async function resolveImportPending(importId, pendingId, codigoGmus) {
  const csrfToken = await getCsrfToken();
  return apiRequest(`/api/importacoes/${importId}/pendencias/${pendingId}/resolver/`, {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken, "Content-Type": "application/json" },
    body: JSON.stringify({ codigo_gmus: codigoGmus }),
  });
}

async function uploadReport(reportType, file, { reimportar = false } = {}) {
  const csrfToken = await getCsrfToken();
  const formData = new FormData();
  formData.append("arquivo", file);
  if (reimportar) formData.append("reimportar", "true");

  return apiRequest(`/api/importacoes/${reportType}/`, {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken },
    body: formData,
  });
}
