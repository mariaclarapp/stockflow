import { apiRequest } from "./client";
import { getCsrfToken } from "./csrf";

export function getMovementValidation(competencia, ups) {
  const params = new URLSearchParams({ competencia: String(competencia), ups: String(ups) });
  return apiRequest(`/api/estoques/validacao-movimentacoes/?${params.toString()}`);
}

export async function correctMovementValidation({
  competencia,
  ups,
  medicamento,
  estoqueCorrigido,
  justificativa,
}) {
  const csrfToken = await getCsrfToken();
  return apiRequest("/api/estoques/validacao-movimentacoes/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({
      competencia,
      ups,
      medicamento,
      estoque_corrigido: estoqueCorrigido,
      justificativa,
    }),
  });
}

export function getAnalysisOptions() {
  return Promise.all([
    apiRequest("/api/competencias/", { cache: "no-store" }),
    apiRequest("/api/ups/", { cache: "no-store" }),
    apiRequest("/api/subgrupos-gmus/", { cache: "no-store" }),
    apiRequest("/api/classificacoes/", { cache: "no-store" }),
    apiRequest("/api/medicamentos/opcoes/?contrato_estoque=2", { cache: "no-store" }),
  ]).then(([competencias, ups, subgrupos, classificacoes, medicationOptions]) => ({
    competencias,
    ups,
    subgrupos,
    classificacoes,
    unidades: medicationOptions.unidades || [],
  }));
}

export function getConsumptionAnalysis({
  competenceStart,
  competenceEnd,
  upsId = "",
  search = "",
  category = "",
  unit = "",
  comparisonEnabled = false,
  comparisonStart = "",
  comparisonEnd = "",
}) {
  const params = new URLSearchParams({
    competencia_inicial: String(competenceStart),
    competencia_final: String(competenceEnd),
  });
  if (upsId) params.set("ups", upsId);
  if (search.trim()) params.set("busca", search.trim());
  if (unit) params.set("unidade", unit);
  if (category) {
    const [type, id] = category.split(":");
    params.set(type, id);
  }
  if (comparisonEnabled && comparisonStart && comparisonEnd) {
    params.set("comparacao_inicial", comparisonStart);
    params.set("comparacao_final", comparisonEnd);
  }
  return apiRequest(`/api/analises/consumo/?${params.toString()}`);
}
