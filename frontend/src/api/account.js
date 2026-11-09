import { apiRequest } from "./client";
import { getCsrfToken } from "./csrf";

export async function changePassword({ currentPassword, password, passwordConfirmation }) {
  const csrfToken = await getCsrfToken();
  return apiRequest("/api/auth/password/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({
      current_password: currentPassword,
      password,
      password_confirmation: passwordConfirmation,
    }),
  });
}
