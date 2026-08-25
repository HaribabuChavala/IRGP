import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Bell,
  Building2,
  CreditCard,
  Database,
  LayoutDashboard,
  MessageSquare,
  UserPlus,
  Users,
  Clock,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

export const platformAdminNav: NavItem[] = [
  { label: "Dashboard", href: "/admin/dashboard", icon: LayoutDashboard },
  { label: "Register Organization", href: "/admin/organizations/register", icon: Building2 },
  { label: "Register Users", href: "/admin/users/register", icon: UserPlus },
];

export const orgNav: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Instant Reports", href: "/reports", icon: MessageSquare },
  { label: "Data Sources", href: "/data-sources", icon: Database, adminOnly: true },
  { label: "Subscriptions", href: "/subscriptions", icon: CreditCard, adminOnly: true },
  { label: "Logs", href: "/logs", icon: Activity },
  { label: "Notifications", href: "/notifications", icon: Bell },
  { label: "Reminders", href: "/reminders", icon: Clock },
];
