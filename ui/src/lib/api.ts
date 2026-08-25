import { env } from "@/config/env";
import { ensureValidAccessToken } from "@/lib/keycloak";
import type {
  DataSource,
  Notification,
  Organization,
  PlatformStats,
  QueryHistoryItem,
  SubscriptionPlan,
  SubscriptionPlanDetails,
  SubscriptionReminder,
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

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await ensureValidAccessToken();
  const headers: HeadersInit = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
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
    }>("/api/v1/org/dashboard"),

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

  generateReport: (prompt: string, dataSourceId: string) =>
    apiFetch<{ jobId: string }>("/api/v1/reports/generate", {
      method: "POST",
      body: JSON.stringify({ prompt, dataSourceId }),
    }),
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
