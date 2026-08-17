import { apiRequest } from "./client";

export async function getCsrfToken() {
  const data = await apiRequest("/api/auth/csrf/");

  if (!data?.csrfToken) {
    throw new Error("Resposta CSRF inválida.");
  }

  return data.csrfToken;
}
