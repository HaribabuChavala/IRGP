"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileBarChart2, Shield, User, Users } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { useAuth } from "@/components/auth/AuthProvider";

const DEMO_ACCOUNTS = [
  {
    username: "platform-admin",
    password: "platform-admin-password",
    label: "Platform Admin",
    icon: Shield,
  },
  {
    username: "org-admin",
    password: "org-admin-password",
    label: "Organization Admin",
    icon: Users,
  },
  {
    username: "report-user",
    password: "report-user-password",
    label: "Organization User",
    icon: User,
  },
];

export default function LoginPage() {
  const { login, isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading || !isAuthenticated || !user) return;
    router.replace(user.role === "PLATFORM_ADMIN" ? "/admin/dashboard" : "/dashboard");
  }, [isAuthenticated, isLoading, user, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-lg">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600">
            <FileBarChart2 className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Sign in</h1>
          <p className="mt-2 text-sm text-slate-500">
            Sign in with Keycloak to access the Instant Report Generation Platform
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Keycloak Authentication</CardTitle>
            <CardDescription>
              Realm: <code className="rounded bg-slate-100 px-1 text-xs">report-platform</code>
              {" · "}
              Client: <code className="rounded bg-slate-100 px-1 text-xs">report-platform-ui</code>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button className="w-full" size="lg" onClick={login} disabled={isLoading}>
              Sign in with Keycloak
            </Button>

            <div className="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Demo accounts
              </p>
              <ul className="mt-3 space-y-2">
                {DEMO_ACCOUNTS.map(({ username, password, label, icon: Icon }) => (
                  <li key={username} className="flex items-center gap-2 text-sm text-slate-600">
                    <Icon className="h-4 w-4 text-slate-400" />
                    <span className="font-medium text-slate-800">{label}</span>
                    <span className="text-slate-400">·</span>
                    <code className="text-xs">{username}</code>
                    <span className="text-slate-400">/</span>
                    <code className="text-xs">{password}</code>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        <p className="mt-6 text-center text-sm text-slate-500">
          <Link href="/" className="text-indigo-600 hover:underline">
            Back to home
          </Link>
        </p>
      </div>
    </div>
  );
}
