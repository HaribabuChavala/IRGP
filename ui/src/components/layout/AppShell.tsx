"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import type { NavItem } from "@/config/navigation";

interface AppShellProps {
  navItems: NavItem[];
  sidebarTitle: string;
  sidebarSubtitle?: string;
  headerTitle: string;
  headerDescription?: string;
  isAdmin?: boolean;
  userName?: string;
  userRole?: string;
  notificationCount?: number;
  children: React.ReactNode;
}

export function AppShell({
  navItems,
  sidebarTitle,
  sidebarSubtitle,
  headerTitle,
  headerDescription,
  isAdmin,
  userName,
  userRole,
  notificationCount,
  children,
}: AppShellProps) {
  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar
        items={navItems}
        title={sidebarTitle}
        subtitle={sidebarSubtitle}
        isAdmin={isAdmin}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          title={headerTitle}
          description={headerDescription}
          userName={userName}
          userRole={userRole}
          notificationCount={notificationCount}
        />
        <main className="flex-1 overflow-y-auto p-8">{children}</main>
      </div>
    </div>
  );
}
