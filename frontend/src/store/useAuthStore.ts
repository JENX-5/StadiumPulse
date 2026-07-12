import { create } from "zustand";
import { persist } from "zustand/middleware";

import { AUTH_COOKIE_NAME, UserRole } from "@/lib/auth-constants";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  venue_id: string | null;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (token: string, user: AuthUser) => void;
  logout: () => void;
}

function setAuthCookie(token: string) {
  if (typeof document === "undefined") return;
  // Non-httpOnly by necessity: the frontend (localhost:3000) and API
  // (localhost:8000) are different origins in dev, so we attach the token
  // to requests explicitly via the Authorization header (see api-client.ts)
  // rather than relying on the browser to send it automatically. The
  // cookie's only job is letting `middleware.ts` (edge, no localStorage
  // access) see whether/who is logged in for route guarding.
  const maxAgeSeconds = 60 * 60 * 24; // 24h; keep in sync with backend JWT_EXPIRE_MINUTES default
  document.cookie = `${AUTH_COOKIE_NAME}=${token}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax`;
}

function clearAuthCookie() {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      login: (token, user) => {
        setAuthCookie(token);
        set({ token, user, isAuthenticated: true });
      },
      logout: () => {
        clearAuthCookie();
        set({ token: null, user: null, isAuthenticated: false });
      },
    }),
    { name: "stadiumpulse-auth" }
  )
);
