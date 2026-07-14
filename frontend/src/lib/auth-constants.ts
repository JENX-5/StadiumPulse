/**
 * Shared between `middleware.ts` (edge runtime), `useAuthStore.ts`, and
 * `api-client.ts`. Kept dependency-free so it's safe to import from the
 * edge runtime.
 */
export const AUTH_COOKIE_NAME = "sp_token";

export type UserRole = "admin" | "dispatcher" | "volunteer" | "fan";

/** Where each role lands after login, and what "/" resolves to for them. */
export const ROLE_HOME_ROUTE: Record<UserRole, string> = {
  admin: "/",
  dispatcher: "/",
  volunteer: "/",
  fan: "/fan",
};

export interface DecodedAccessToken {
  sub: string;
  role: UserRole;
  exp: number;
  iat: number;
  type: string;
}

/**
 * Decode a JWT payload WITHOUT verifying the signature.
 *
 * This is only ever used for UX-level routing decisions (which dashboard
 * to land on, whether to bounce to /login) in `middleware.ts`. It is never
 * treated as an authorization boundary — every API request is still
 * verified and signature-checked server-side by the backend's
 * `get_current_user` / `RequireRole` dependencies.
 */
export function decodeAccessToken(token: string): DecodedAccessToken | null {
  try {
    const payloadSegment = token.split(".")[1];
    if (!payloadSegment) return null;

    const base64 = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const json = atob(padded);
    return JSON.parse(json) as DecodedAccessToken;
  } catch {
    return null;
  }
}

export function isTokenExpired(decoded: DecodedAccessToken): boolean {
  return decoded.exp * 1000 <= Date.now();
}
