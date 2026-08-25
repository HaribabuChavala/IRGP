"use client";

import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { roleLabel, useAuth } from "@/components/auth/AuthProvider";
import { platformAdminNav } from "@/config/navigation";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  return (
    <RequireAuth allowedRoles={["PLATFORM_ADMIN"]}>
      {user && (
        <AppShell
        navItems={platformAdminNav}
        sidebarTitle="Platform Admin"
        sidebarSubtitle="Instant Report Generation"
        headerTitle="Platform Administration"
        userName={user.name}
        userRole={roleLabel(user.role)}
      >
        {children}
      </AppShell>
      )}
    </RequireAuth>
  );
}
