import { apiRequest } from "./client";
import { getCsrfToken } from "./csrf";

export async function uploadInventory(file) {
  const csrfToken = await getCsrfToken();
  const formData = new FormData();
  formData.append("arquivo", file);

  return apiRequest("/api/importacoes/inventario/", {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken },
    body: formData,
  });
}
