import { apiRequest } from "./client";
import { getCsrfToken } from "./csrf";

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
