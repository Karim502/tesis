const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000/api").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(status, code, message, details = null) {
    super(message);
    this.details = details;
    this.status = status;
    this.code = code;
  }
}

function extractError(status, data) {
  const detail = data?.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    return { code: detail.code ?? null, message: detail.message || "Error", details: detail };
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    return {
      code: "VALIDATION_ERROR",
      message: first?.msg || "Datos inválidos",
      details: detail,
    };
  }
  if (typeof detail === "string") {
    return { code: null, message: detail, details: null };
  }
  if (status === 429) {
    return { code: "RATE_LIMITED", message: "Demasiadas solicitudes. Intenta en unos segundos.", details: null };
  }
  if (status === 502 || status === 503 || status === 504) {
    return { code: "SERVER_STARTING", message: "El servidor está iniciando. Intenta nuevamente en unos segundos.", details: null };
  }
  return { code: null, message: "Error inesperado del servidor", details: null };
}

export async function apiFetch(path, { method = "GET", body, signal } = {}) {
  const isFormData = body instanceof FormData;

  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      signal,
      credentials: "include",
      headers: body && !isFormData ? { "Content-Type": "application/json" } : undefined,
      body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
    });
  } catch (e) {
    if (e?.name === "AbortError") throw e;
    throw new ApiError(0, "NETWORK_ERROR", "Sin conexión con el servidor");
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    if (res.status === 401 && !path.startsWith("/auth/")) {
      window.dispatchEvent(new CustomEvent("auth:expired"));
    }
    const { code, message, details } = extractError(res.status, data);
    throw new ApiError(res.status, code, message, details);
  }
  return data;
}

export const authApi = {
  login: (email, password) => apiFetch("/auth/login", { method: "POST", body: { email, password } }),
  logout: () => apiFetch("/auth/logout", { method: "POST" }),
  me: () => apiFetch("/auth/me"),
};