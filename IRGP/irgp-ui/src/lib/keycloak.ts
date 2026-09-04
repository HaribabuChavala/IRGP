import Keycloak from "keycloak-js";
import { env } from "@/config/env";

const RETURN_TO_KEY = "report_platform_return_to";

let keycloakInstance: Keycloak | null = null;

export function setAuthReturnTarget(path: string = "/dashboard"): void {
  if (typeof window === "undefined") return;

  try {
    // Allow callers to pass a full URL or a path with query string.
    const url = new URL(path, window.location.origin);
    const pathname = url.pathname || "/";
    const search = url.search || "";

    // Don't store redirects back to login or the callback itself — use dashboard instead.
    if (pathname === "/login" || pathname === "/auth/callback") {
      sessionStorage.setItem(RETURN_TO_KEY, "/dashboard");
      return;
    }

    const safePath = pathname.startsWith("/") ? `${pathname}${search}` : "/dashboard";
    // Store only the path + query portion to avoid origin-sensitive values.
    sessionStorage.setItem(RETURN_TO_KEY, safePath);
  } catch {
    sessionStorage.setItem(RETURN_TO_KEY, "/dashboard");
  }
}

export function getAuthReturnTarget(defaultPath: string = "/dashboard"): string {
  if (typeof window === "undefined") return defaultPath;

  const stored = sessionStorage.getItem(RETURN_TO_KEY) || defaultPath;
  // Accept values that might mistakenly include an origin (full URL).
  try {
    if (stored.startsWith("http://") || stored.startsWith("https://")) {
      const parsed = new URL(stored);
      const pathAndSearch = `${parsed.pathname}${parsed.search || ""}`;
      return pathAndSearch.startsWith("/") ? pathAndSearch : defaultPath;
    }
  } catch {
    // fallthrough to default handling
  }

  return stored.startsWith("/") ? stored : defaultPath;
}

export function clearAuthReturnTarget(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(RETURN_TO_KEY);
}

export function getKeycloak(): Keycloak | null {
  if (typeof window === "undefined") return null;
  if (!keycloakInstance) {
    keycloakInstance = new Keycloak({
      url: env.keycloakUrl,
      realm: env.keycloakRealm,
      clientId: env.keycloakClientId,
    });
  }
  return keycloakInstance;
}

export function getAccessToken(): string | undefined {
  return getKeycloak()?.token;
}

export async function ensureValidAccessToken(): Promise<string | undefined> {
  const kc = getKeycloak();
  if (!kc) return undefined;

  try {
    if (kc.token && !kc.isTokenExpired(30)) {
      return kc.token;
    }

    if (kc.refreshToken) {
      const refreshed = await kc.updateToken(30);
      if (refreshed) {
        return kc.token ?? undefined;
      }
    }

    return kc.token ?? undefined;
  } catch {
    return undefined;
  }
}

export function getAuthRedirectUri(): string {
  return `${window.location.origin}/auth/callback`;
}
