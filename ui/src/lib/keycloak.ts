import Keycloak from "keycloak-js";
import { env } from "@/config/env";

const RETURN_TO_KEY = "report_platform_return_to";

let keycloakInstance: Keycloak | null = null;

export function setAuthReturnTarget(path: string = "/dashboard"): void {
  if (typeof window === "undefined") return;

  const safePath = path.startsWith("/") ? path : "/dashboard";
  sessionStorage.setItem(RETURN_TO_KEY, safePath);
}

export function getAuthReturnTarget(defaultPath: string = "/dashboard"): string {
  if (typeof window === "undefined") return defaultPath;

  const stored = sessionStorage.getItem(RETURN_TO_KEY) || defaultPath;
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
