"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type Keycloak from "keycloak-js";
import type { AuthUser, UserRole } from "@/lib/types";
import { getAuthRedirectUri, getKeycloak, setAuthReturnTarget } from "@/lib/keycloak";

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  getToken: () => string | undefined;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function mapKeycloakUser(kc: Keycloak): AuthUser {
  const parsed = kc.tokenParsed as Record<string, unknown> | undefined;
  const roles =
    (parsed?.realm_access as { roles?: string[] } | undefined)?.roles ?? [];

  let role: UserRole = "ORG_USER";
  if (roles.includes("PLATFORM_ADMIN")) role = "PLATFORM_ADMIN";
  else if (roles.includes("REPORT_ADMIN")) role = "ORG_ADMIN";

  const givenName = parsed?.given_name as string | undefined;
  const familyName = parsed?.family_name as string | undefined;
  const username = parsed?.preferred_username as string | undefined;
  const email = (parsed?.email as string) ?? "";

  const fallbackOrganizationId =
    username === "hari" || username === "alex" ? "org-spartexai" : undefined;
  const fallbackOrganizationName =
    username === "hari" || username === "alex" ? "Spartexai" : undefined;

  return {
    id: kc.subject ?? "",
    name: [givenName, familyName].filter(Boolean).join(" ") || username || "User",
    email,
    role,
    organizationId: ((parsed?.tenant_id as string) || fallbackOrganizationId) || undefined,
    organizationName: ((parsed?.organization_name as string) || fallbackOrganizationName) || undefined,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const kc = getKeycloak();
    if (!kc) {
      setIsLoading(false);
      return;
    }

    kc.init({
      onLoad: "check-sso",
      pkceMethod: "S256",
      checkLoginIframe: false,
    })
      .then((authenticated) => {
        setIsAuthenticated(authenticated);
        if (authenticated) {
          setUser(mapKeycloakUser(kc));
        }
        kc.onTokenExpired = () => {
          kc.updateToken(30).catch(() => {
            setUser(null);
            setIsAuthenticated(false);
            kc.logout({ redirectUri: window.location.origin });
          });
        };
      })
      .catch(() => {
        setIsAuthenticated(false);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(() => {
    // Use the pathname (ignore query/hash) when deciding if we're on the login/callback page
    const currentPath = typeof window !== "undefined" ? window.location.pathname : "/dashboard";
    const shouldDefault = currentPath === "/login" || currentPath === "/auth/callback";
    const fullPath = typeof window !== "undefined" ? `${window.location.pathname}${window.location.search}` : "/dashboard";
    const target = shouldDefault ? "/dashboard" : fullPath;
    setAuthReturnTarget(target);

    const kc = getKeycloak();
    kc?.login({ redirectUri: getAuthRedirectUri() });
  }, []);

  const logout = useCallback(() => {
    const kc = getKeycloak();
    setUser(null);
    setIsAuthenticated(false);
    kc?.logout({ redirectUri: `${window.location.origin}/login` });
  }, []);

  const getToken = useCallback(() => getKeycloak()?.token, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated,
      isLoading,
      login,
      logout,
      getToken,
    }),
    [user, isAuthenticated, isLoading, login, logout, getToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function roleLabel(role: UserRole): string {
  switch (role) {
    case "PLATFORM_ADMIN":
      return "Platform Admin";
    case "ORG_ADMIN":
      return "Organization Admin";
    case "ORG_USER":
      return "Organization User";
  }
}

export function isOrgAdmin(role: UserRole): boolean {
  return role === "ORG_ADMIN" || role === "PLATFORM_ADMIN";
}
