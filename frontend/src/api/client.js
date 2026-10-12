const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(status, code, message, details = null) {
    super(message);
    this.details = details;
    this.status = status;
    this.code = code;
  }
}

/**
 * Wrapper de fetch.
 * `credentials: "include"` hace que el navegador envíe la cookie HttpOnly con el JWT.
 * El token nunca pasa por JavaScript: no se guarda en localStorage ni en memoria,
 * por lo que un XSS no puede extraerlo.
 */
export async function apiFetch(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      credentials: "include",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Sin conexión con el servidor");
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const detail = data?.detail;
    const isObj = detail && typeof detail === "object" && !Array.isArray(detail);
    throw new ApiError(res.status, isObj ? detail.code : null, isObj ? detail.message : "Error", isObj ? detail : null);
  }
  return data;
}

export const authApi = {
  login: (email, password) => apiFetch("/auth/login", { method: "POST", body: { email, password } }),
  logout: () => apiFetch("/auth/logout", { method: "POST" }),
  me: () => apiFetch("/auth/me"),
};
