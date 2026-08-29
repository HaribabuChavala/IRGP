export const env = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://report.localhost",
  billingApiBaseUrl: process.env.NEXT_PUBLIC_BILLING_API_BASE_URL ?? "http://billing.localhost",
  paymentApiBaseUrl: process.env.NEXT_PUBLIC_PAYMENT_API_BASE_URL ?? "http://payment.localhost",
  keycloakUrl: process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "http://localhost:8081",
  keycloakRealm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "report-platform",
  keycloakClientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "report-platform-ui",
};
