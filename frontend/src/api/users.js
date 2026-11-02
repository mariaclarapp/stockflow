import { apiRequest } from "./client";
import { getCsrfToken } from "./csrf";

export function getStaffUsers() {
  return apiRequest("/api/usuarios/funcionarios/", { cache: "no-store" });
}

export async function createStaffUser({ name, username, password, passwordConfirmation }) {
  const csrfToken = await getCsrfToken();
  return apiRequest("/api/usuarios/funcionarios/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({
      nome: name,
      username,
      password,
      password_confirmation: passwordConfirmation,
    }),
  });
}
