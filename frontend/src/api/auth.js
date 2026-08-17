import { apiRequest } from "./client";

async function getCsrfToken() {
  const data = await apiRequest("/api/auth/csrf/");

  if (!data?.csrfToken) {
    throw new Error("Resposta CSRF inválida.");
  }

  return data.csrfToken;
}

export async function loginWithSession(credentials) {
  const csrfToken = await getCsrfToken();

  return apiRequest("/api/auth/login/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify(credentials),
  });
}

export function getCurrentUser() {
  return apiRequest("/api/auth/me/");
}

export async function logoutSession() {
  const csrfToken = await getCsrfToken();

  return apiRequest("/api/auth/logout/", {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken },
  });
}
