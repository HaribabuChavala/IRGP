export type SubscriptionPlan = "free" | "half_year" | "year";

export type UserRole = "PLATFORM_ADMIN" | "ORG_ADMIN" | "ORG_USER";

export type DataSourceType = "oracle" | "teradata" | "hive" | "excel" | "jdbc";

export interface Organization {
  id: string;
  name: string;
  plan: SubscriptionPlan;
  status: "active" | "suspended" | "trial";
  userCount: number;
  dataSourceCount: number;
  queriesThisMonth: number;
  createdAt: string;
}

export interface PlatformStats {
  totalOrganizations: number;
  activeJobs: number;
  queriesToday: number;
  utilizationPercent: number;
}

export interface OrgUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  organizationId: string;
  status: "active" | "invited" | "disabled";
  lastLogin?: string;
}

export interface DataSource {
  id: string;
  name: string;
  type: DataSourceType;
  connectionUrl?: string;
  host?: string;
  port?: number;
  database?: string;
  schema?: string;
  filePath?: string;
  status: "connected" | "disconnected" | "error";
  accessMode?: "read" | "write" | "unknown";
  lastValidatedAt?: string;
  lastUsed?: string;
  queryCount: number;
}

export interface QueryHistoryItem {
  id: string;
  prompt: string;
  dataSourceId: string;
  dataSourceName: string;
  executedAt: string;
  status: "completed" | "failed" | "running";
  rowCount?: number;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: "report" | "subscription" | "system";
  read: boolean;
  createdAt: string;
}

export interface SubscriptionReminder {
  id: string;
  message: string;
  plan: SubscriptionPlan;
  expiresAt: string;
  daysRemaining: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  exportable?: boolean;
  tableData?: string[][];
}

export interface SubscriptionPlanDetails {
  id: SubscriptionPlan;
  name: string;
  price: string;
  period: string;
  features: string[];
  queryLimit: number;
  dataSourceLimit: number;
  highlighted?: boolean;
}

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  organizationId?: string;
  organizationName?: string;
}
