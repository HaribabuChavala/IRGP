export const env = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://report.localhost",
  keycloakUrl: process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "http://localhost:8081",
  keycloakRealm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "report-platform",
  keycloakClientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "report-platform-ui",
};
