import { config } from "@/lib/config";
import { useAuthStore } from "@/store/useAuthStore";

export class ApiError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Set true for form-urlencoded bodies (e.g. the OAuth2 /auth/token route). */
  form?: boolean;
  headers?: Record<string, string>;
}

/**
 * Shared fetch wrapper for every backend call. Attaches the JWT from
 * `useAuthStore` as `Authorization: Bearer <token>`, normalizes the
 * backend's `{ error: { code, message, details } }` envelope (see
 * `app/core/exceptions.py`) into an `ApiError`, and forces a logout on 401
 * so a stale/expired token doesn't cause a wall of silent failures.
 */
export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { method = "GET", body, form = false, headers = {} } = options;

  const token = useAuthStore.getState().token;
  const requestHeaders: Record<string, string> = { ...headers };

  if (token) {
    requestHeaders["Authorization"] = `Bearer ${token}`;
  }

  let requestBody: BodyInit | undefined;
  if (body !== undefined) {
    if (form) {
      requestHeaders["Content-Type"] = "application/x-www-form-urlencoded";
      requestBody = body as string;
    } else {
      requestHeaders["Content-Type"] = "application/json";
      requestBody = JSON.stringify(body);
    }
  }

  const response = await fetch(`${config.apiUrl}${path}`, {
    method,
    headers: requestHeaders,
    body: requestBody,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    if (response.status === 401) {
      // Stale/expired/invalid token — clear it so the UI reflects logged-out
      // state and middleware sends the user back to /login on next nav.
      useAuthStore.getState().logout();
    }

    const errorEnvelope = payload?.error;
    throw new ApiError(
      response.status,
      errorEnvelope?.code ?? "unknown_error",
      errorEnvelope?.message ?? response.statusText ?? "Request failed",
      errorEnvelope?.details ?? {}
    );
  }

  return payload as T;
}
