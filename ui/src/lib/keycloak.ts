import Keycloak from "keycloak-js";
import { env } from "@/config/env";

let keycloakInstance: Keycloak | null = null;

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
