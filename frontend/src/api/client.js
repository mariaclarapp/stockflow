const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export const AUTH_INVALID_EVENT = "stockflow:auth-invalid";

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiRequest(path, options = {}) {
  const {
    notifyAuthFailure = true,
    credentials = "include",
    ...fetchOptions
  } = options;
  let response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      ...fetchOptions,
      credentials,
      headers: {
        Accept: "application/json",
        ...fetchOptions.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Não foi possível conectar ao servidor. Tente novamente.",
    );
  }

  const hasJson = response.headers
    .get("content-type")
    ?.includes("application/json");
  const data = hasJson ? await response.json() : null;

  if (!response.ok) {
    if (
      notifyAuthFailure &&
      (response.status === 401 || response.status === 403)
    ) {
      window.dispatchEvent(new CustomEvent(AUTH_INVALID_EVENT));
    }
    throw new ApiError(
      data?.detail || data?.erro || "Não foi possível concluir a solicitação.",
      response.status,
    );
  }

  return data;
}
