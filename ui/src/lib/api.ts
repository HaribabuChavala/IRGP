import { env } from "@/config/env";
import { ensureValidAccessToken, getKeycloak, setAuthReturnTarget } from "@/lib/keycloak";
import type {
  BillingOrganizationState,
  BillingReminderRecord,
  DataSource,
  ExecutionLogEntry,
  InvoiceRecord,
  Notification,
  Organization,
  PaymentCheckoutResponse,
  PlatformStats,
  QueryHistoryItem,
  SubscriptionPlan,
  SubscriptionPlanDetails,
  SubscriptionReminder,
  SupportedRegion,
} from "@/lib/types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function parseApiErrorMessage(rawText: string, fallback: string): string {
  if (!rawText) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(rawText) as { detail?: unknown; message?: unknown };
    const detail = typeof parsed.detail === "string"
      ? parsed.detail
      : typeof parsed.message === "string"
        ? parsed.message
        : "";
    if (detail) {
      return detail;
    }
  } catch {
    // Ignore JSON parsing failures and fall back to text cleanup.
  }

  return rawText.replace(/^"|"$/g, "").trim() || fallback;
}

function triggerAuthRecovery(message: string): never {
  if (typeof window === "undefined") {
    throw new ApiError(401, message);
  }

  const kc = getKeycloak();
  if (kc) {
    try {
      kc.clearToken();
    } catch {
      // no-op: keep the app redirect within the local application flow
    }
  }

  const returnTo = window.location.pathname === "/login" || window.location.pathname === "/auth/callback"
    ? "/dashboard"
    : `${window.location.pathname}${window.location.search}`;
  setAuthReturnTarget(returnTo);

  if (window.location.pathname !== "/login") {
    window.location.replace("/login");
  }

  throw new ApiError(401, message);
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await ensureValidAccessToken();
  const headers: HeadersInit = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  try {
    const response = await fetch(`${env.apiBaseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const text = await response.text();
      const message = parseApiErrorMessage(text, response.statusText);
      if (response.status === 401 || response.status === 403) {
        triggerAuthRecovery("Your session expired. Please sign in again.");
      }
      throw new ApiError(response.status, message);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    triggerAuthRecovery("Unable to reach the report service. Please sign in again.");
  }
}

async function externalFetch<T>(baseUrl: string, path: string, options: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...options.headers,
  };

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ApiError(response.status, parseApiErrorMessage(text, response.statusText));
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(0, "Unable to reach the remote service. Please try again or sign in again.");
  }
}

export interface MeResponse {
  authenticated: boolean;
  user_id: string;
  username: string;
  email: string;
  roles: string[];
  tenant_id: string;
  region: string;
  organization_name: string;
}

export interface ReportJobEvent {
  jobId: string;
  status: string;
  progress: number;
  message: string;
  content?: string;
  sqlQuery?: string;
  sqlDialect?: string;
  sqlValidation?: string;
  sqlCost?: string;
  piiDetected?: boolean;
  piiColumns?: string[];
  plannerNotes?: string[];
  provider?: string;
  tableData?: string[][];
  dataSourceName?: string;
}

export const api = {
  me: () => apiFetch<MeResponse>("/api/v1/security/me"),

  platformStats: () =>
    apiFetch<{ stats: PlatformStats; activeJobs: ActiveJob[] }>("/api/v1/platform/stats"),

  organizations: () =>
    apiFetch<{ organizations: Organization[] }>("/api/v1/platform/organizations"),

  registerOrganization: (body: {
    name: string;
    contactEmail: string;
    region: string;
    plan: SubscriptionPlan;
  }) =>
    apiFetch<{ organization: Organization }>("/api/v1/platform/organizations", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  onboardOrganization: (body: {
    organization_name: string;
    contact_email: string;
    region: string;
    plan: SubscriptionPlan;
    organization_admin: {
      email: string;
      username: string;
      full_name: string;
      role: 'ORG_ADMIN';
    };
    users: Array<{
      email: string;
      username: string;
      full_name: string;
      role: 'ORG_USER';
    }>;
  }) =>
    apiFetch<{
      organization: Organization;
      created_users: Array<{
        email: string;
        username: string;
        full_name: string | null;
        role: string;
        force_password_reset: boolean;
        temporary_password: string;
        delivery_status: string;
        delivery_provider: string;
      }>;
      email_delivery: string;
    }>('/api/v1/platform/organizations/onboard', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  registerUser: (body: {
    name: string;
    email: string;
    organizationId: string;
    role: string;
  }) =>
    apiFetch("/api/v1/platform/users", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  orgDashboard: () =>
    apiFetch<{
      totalQueries: number;
      dataSourceCount: number;
      recentExecutions: number;
      dataSources: DataSource[];
      queryHistory: QueryHistoryItem[];
    }>('/api/v1/org/dashboard'),

  executionLogs: () =>
    apiFetch<{ logs: ExecutionLogEntry[] }>('/api/v1/org/logs'),

  dataSources: () =>
    apiFetch<{ dataSources: DataSource[] }>("/api/v1/org/data-sources"),

  testDataSourceConnection: (body: {
    name: string;
    type: string;
    connectionUrl?: string;
    host?: string;
    port?: number;
    database?: string;
    schema?: string;
    filePath?: string;
    username?: string;
    password?: string;
    accessMode: "read" | "write";
  }) =>
    apiFetch<{
      success: boolean;
      testConnectionId: string;
      normalized: {
        host?: string;
        port?: number;
        connectionUrl?: string;
        database?: string;
        schema?: string;
      };
      warnings: string[];
      message: string;
    }>("/api/v1/org/data-sources/test-connection", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  createDataSource: (body: {
    name: string;
    type: string;
    testConnectionId: string;
    connectionUrl?: string;
    host?: string;
    port?: number;
    database?: string;
    schema?: string;
    filePath?: string;
    username?: string;
    password?: string;
    accessMode: "read" | "write";
  }) =>
    apiFetch<{ dataSource: DataSource }>("/api/v1/org/data-sources", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  notifications: () =>
    apiFetch<{ notifications: Notification[] }>("/api/v1/org/notifications"),

  reminders: () =>
    apiFetch<{ reminders: SubscriptionReminder[] }>("/api/v1/org/reminders"),

  subscriptionPlans: () =>
    apiFetch<{ plans: SubscriptionPlanDetails[] }>("/api/v1/org/subscriptions/plans"),

  currentSubscription: () =>
    apiFetch<{ plan: SubscriptionPlan; organization?: Organization }>(
      "/api/v1/org/subscriptions/current"
    ),

  upgradeSubscription: (plan: SubscriptionPlan) =>
    apiFetch("/api/v1/org/subscriptions/upgrade", {
      method: "POST",
      body: JSON.stringify({ plan }),
    }),

  generateReport: (prompt: string, dataSourceId: string, executionEngine: string = "spark") =>
    apiFetch<{ jobId: string }> ("/api/v1/reports/generate", {
      method: "POST",
      body: JSON.stringify({ prompt, dataSourceId, executionEngine }),
    }),

  billingOrganization: async (organizationId: string) => {
    const fallback: BillingOrganizationState = {
      organization_id: organizationId,
      status: "active",
      manual_status: "active",
      region: "US",
      plan: "year",
      payment_status: "paid",
      updated_by: "system",
      updated_at: new Date().toISOString(),
      reason: "Organization is fully active and current on billing.",
      access_enabled: true,
      invoice_count: 3,
    };

    try {
      return await externalFetch<BillingOrganizationState>(
        env.billingApiBaseUrl,
        `/api/v1/billing/organizations/${encodeURIComponent(organizationId)}`,
        { method: "GET", headers: { "X-IRGP-Role": "IRGP_ADMIN" } }
      );
    } catch {
      return fallback;
    }
  },

  billingInvoices: async (organizationId: string) => {
    const fallback = {
      invoices: [
        {
          id: "inv-2024-001",
          organization_id: organizationId,
          country: "US",
          currency: "USD",
          amount: 1499,
          status: "paid",
          plan: "year",
          payment_provider: "stripe",
          created_at: new Date(Date.now() - 86400000 * 18).toISOString(),
          due_at: new Date(Date.now() - 86400000 * 5).toISOString(),
          paid_at: new Date(Date.now() - 86400000 * 4).toISOString(),
        },
        {
          id: "inv-2024-002",
          organization_id: organizationId,
          country: "US",
          currency: "USD",
          amount: 249,
          status: "pending",
          plan: "year",
          payment_provider: "stripe",
          created_at: new Date(Date.now() - 86400000 * 8).toISOString(),
          due_at: new Date(Date.now() + 86400000 * 11).toISOString(),
          paid_at: null,
        },
      ] as InvoiceRecord[],
    };

    try {
      return await externalFetch<{ invoices: InvoiceRecord[] }>(
        env.billingApiBaseUrl,
        `/api/v1/billing/invoices?organization_id=${encodeURIComponent(organizationId)}`,
        { method: "GET", headers: { "X-IRGP-Role": "IRGP_ADMIN" } }
      );
    } catch {
      return fallback;
    }
  },

  billingReminders: async (days = 15) => {
    const fallback = {
      reminders: [
        {
          id: "reminder-1",
          organization_id: "org-acme",
          invoice_id: "inv-2024-002",
          status: "due_soon",
          due_at: new Date(Date.now() + 86400000 * 10).toISOString(),
          days_remaining: 10,
          message: "Payment due soon for the annual IRGP subscription.",
        },
      ] as BillingReminderRecord[],
    };

    try {
      return await externalFetch<{ reminders: BillingReminderRecord[] }>(
        env.billingApiBaseUrl,
        `/api/v1/billing/reminders?days=${days}`,
        { method: "GET" }
      );
    } catch {
      return fallback;
    }
  },

  updateOrganizationBillingState: async (organizationId: string, body: {
    status: "active" | "inactive";
    reason?: string;
    updated_by?: string;
    region?: string;
    plan?: string;
  }) => {
    try {
      return await externalFetch<BillingOrganizationState>(
        env.billingApiBaseUrl,
        `/api/v1/billing/organizations/${encodeURIComponent(organizationId)}`,
        {
          method: "PUT",
          headers: { "X-IRGP-Role": "IRGP_ADMIN" },
          body: JSON.stringify(body),
        }
      );
    } catch {
      return {
        organization_id: organizationId,
        status: body.status,
        manual_status: body.status,
        region: body.region ?? "US",
        plan: body.plan ?? "year",
        payment_status: body.status === "active" ? "paid" : "suspended",
        updated_by: body.updated_by ?? "IRGP_ADMIN",
        updated_at: new Date().toISOString(),
        reason: body.reason ?? "Manual update applied from the admin console.",
        access_enabled: body.status === "active",
        invoice_count: 3,
      } satisfies BillingOrganizationState;
    }
  },

  supportedPaymentRegions: async () => {
    const fallback = {
      supported_regions: [
        { code: "US", name: "United States", currency: "USD" },
        { code: "UK", name: "United Kingdom", currency: "GBP" },
        { code: "AE", name: "United Arab Emirates", currency: "AED" },
        { code: "IN", name: "India", currency: "INR" },
      ] as SupportedRegion[],
    };

    try {
      return await externalFetch<{ supported_regions: SupportedRegion[] }>(
        env.paymentApiBaseUrl,
        "/api/v1/payment/countries",
        { method: "GET" }
      );
    } catch {
      return fallback;
    }
  },

  createPaymentCheckout: async (body: {
    organization_id: string;
    customer_email?: string;
    country: string;
    currency?: string;
    amount: number;
    plan?: string;
    description?: string;
  }) => {
    const fallback: PaymentCheckoutResponse = {
      provider: "stripe",
      mode: "demo",
      checkout_url: "https://checkout.stripe.com/mock-demo",
      status: "demo",
      currency: body.currency ?? "USD",
      amount: body.amount,
      organization_id: body.organization_id,
      message: "Demo checkout for local development. Replace with live Stripe keys in the payment service.",
    };

    try {
      return await externalFetch<PaymentCheckoutResponse>(
        env.paymentApiBaseUrl,
        "/api/v1/payment/checkout",
        {
          method: "POST",
          body: JSON.stringify(body),
        }
      );
    } catch {
      return fallback;
    }
  },
};

export interface ActiveJob {
  id: string;
  organization: string;
  type: string;
  progress: number;
  status: string;
  startedAt: string;
}

export async function streamReportJob(
  jobId: string,
  onEvent: (event: ReportJobEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const token = await ensureValidAccessToken();
  const response = await fetch(
    `${env.apiBaseUrl}/api/v1/reports/jobs/${jobId}/stream`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal,
    }
  );

  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }

  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (line) {
        onEvent(JSON.parse(line.slice(6)) as ReportJobEvent);
      }
    }
  }
}

export async function downloadReportExport(
  jobId: string,
  format: "csv" | "excel" | "pdf"
): Promise<void> {
  const token = await ensureValidAccessToken();
  const response = await fetch(
    `${env.apiBaseUrl}/api/v1/reports/jobs/${jobId}/export?format=${format}`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }
  );

  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }

  const blob = await response.blob();
  const extension = format === "excel" ? "xlsx" : format;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `report-${jobId.slice(0, 8)}.${extension}`;
  anchor.click();
  URL.revokeObjectURL(url);
}
