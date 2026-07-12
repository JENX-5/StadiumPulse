import { NextRequest, NextResponse } from "next/server";

import {
  AUTH_COOKIE_NAME,
  ROLE_HOME_ROUTE,
  decodeAccessToken,
  isTokenExpired,
} from "@/lib/auth-constants";

const PUBLIC_PATHS = ["/login"];

function isPublicPath(pathname: string): boolean {
  return (
    PUBLIC_PATHS.some((path) => pathname === path) ||
    pathname.startsWith("/_next") ||
    pathname === "/favicon.ico"
  );
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  const decoded = token ? decodeAccessToken(token) : null;
  const isAuthenticated = !!decoded && !isTokenExpired(decoded);

  // Unauthenticated users: only /login is reachable.
  if (!isAuthenticated) {
    if (isPublicPath(pathname)) {
      return NextResponse.next();
    }
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    const response = NextResponse.redirect(loginUrl);
    if (token) response.cookies.delete(AUTH_COOKIE_NAME); // stale/expired token, clean it up
    return response;
  }

  // Authenticated users shouldn't see the login screen again.
  if (pathname === "/login") {
    return NextResponse.redirect(new URL(ROLE_HOME_ROUTE[decoded.role], request.url));
  }

  // Role-based landing: fans get the limited view, everyone else gets
  // Mission Control. Bounce anyone who's on the "wrong" home route.
  const homeForRole = ROLE_HOME_ROUTE[decoded.role];
  if ((pathname === "/" || pathname === "/fan") && pathname !== homeForRole) {
    return NextResponse.redirect(new URL(homeForRole, request.url));
  }

  return NextResponse.next();
}

export const config = {
  // Run on everything except static assets and Next internals.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
