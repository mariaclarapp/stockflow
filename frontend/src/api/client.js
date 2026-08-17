const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiRequest(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...options.headers,
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
    throw new ApiError(
      data?.detail || data?.erro || "Não foi possível concluir a solicitação.",
      response.status,
    );
  }

  return data;
}
