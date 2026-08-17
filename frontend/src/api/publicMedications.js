import { ApiError, apiRequest } from "./client";

export async function getPublicMedications(search) {
  const query = new URLSearchParams({ search });
  const data = await apiRequest(
    `/api/publico/medicamentos/?${query.toString()}`,
    {
      credentials: "omit",
      notifyAuthFailure: false,
    },
  );

  if (!Array.isArray(data)) {
    throw new ApiError("A API retornou uma resposta inesperada.", 200);
  }

  return data;
}
