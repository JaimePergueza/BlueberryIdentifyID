import type { ApiErrorPayload } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
const TOKEN_KEY = "blueberry-microid.access-token";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

function messageFromPayload(payload: ApiErrorPayload, fallback: string): string {
  if (payload.error?.message) return payload.error.message;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    const messages = payload.detail.map((item) => item.msg).filter(Boolean);
    if (messages.length > 0) return messages.join(". ");
  }
  return fallback;
}

function authenticatedHeaders(init: RequestInit, authenticated: boolean): Headers {
  const headers = new Headers(init.headers);
  const token = authenticated ? getStoredToken() : null;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return headers;
}

async function apiError(response: Response, authenticated: boolean): Promise<ApiError> {
  const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
  const error = new ApiError(
    response.status,
    payload.error?.code ?? "request_failed",
    messageFromPayload(payload, "No se pudo completar la solicitud."),
    payload.error?.request_id,
  );
  if (response.status === 401 && authenticated) {
    clearStoredToken();
    window.dispatchEvent(new CustomEvent("blueberry-auth-expired"));
  }
  return error;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  options: { authenticated?: boolean } = { authenticated: true },
): Promise<T> {
  const authenticated = options.authenticated !== false;
  const headers = authenticatedHeaders(init, authenticated);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 204) return undefined as T;
  if (!response.ok) throw await apiError(response, authenticated);
  return (await response.json()) as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  const headers = authenticatedHeaders({}, true);
  const response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (!response.ok) throw await apiError(response, true);
  return response.blob();
}

export function formBody(values: Record<string, string>): URLSearchParams {
  const body = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => body.set(key, value));
  return body;
}
