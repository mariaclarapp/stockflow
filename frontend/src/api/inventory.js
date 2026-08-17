import { apiRequest } from "./client";
import { getCsrfToken } from "./csrf";

export async function uploadInventory(file, { reimportar = false } = {}) {
  const csrfToken = await getCsrfToken();
  const formData = new FormData();
  formData.append("arquivo", file);
  if (reimportar) formData.append("reimportar", "true");

  return apiRequest("/api/importacoes/inventario/", {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken },
    body: formData,
  });
}
