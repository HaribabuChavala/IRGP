"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { isOrgAdmin, roleLabel, useAuth } from "@/components/auth/AuthProvider";
import { orgNav } from "@/config/navigation";
import { api } from "@/lib/api";

export default function OrgLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user) return;
    api.notifications()
      .then((data) => setUnreadCount(data.notifications.filter((n) => !n.read).length))
      .catch(() => setUnreadCount(0));
  }, [user]);

  return (
    <RequireAuth allowedRoles={["ORG_ADMIN", "ORG_USER", "PLATFORM_ADMIN"]}>
      {user && (
        <AppShell
        navItems={orgNav}
        sidebarTitle="Report Platform"
        sidebarSubtitle={user.organizationName ?? "Organization"}
        headerTitle="Instant Report Generation"
        isAdmin={isOrgAdmin(user.role)}
        userName={user.name}
        userRole={roleLabel(user.role)}
        notificationCount={unreadCount}
      >
        {children}
      </AppShell>
      )}
    </RequireAuth>
  );
}
