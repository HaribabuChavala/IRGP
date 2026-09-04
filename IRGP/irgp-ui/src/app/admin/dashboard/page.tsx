"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, Activity, Zap, TrendingUp, Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import { StatCard } from "@/components/ui/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api, type ActiveJob } from "@/lib/api";
import type { Organization, PlatformStats } from "@/lib/types";

export default function AdminDashboardPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeJobs, setActiveJobs] = useState<ActiveJob[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      router.replace("/login");
      return;
    }

    if (user.role !== "PLATFORM_ADMIN") {
      setError("This page requires the Platform Admin role.");
      setLoading(false);
      logout();
      router.replace("/login");
      return;
    }

    Promise.all([api.platformStats(), api.organizations()])
      .then(([statsData, orgsData]) => {
        setStats(statsData.stats);
        setActiveJobs(statsData.activeJobs);
        setOrganizations(orgsData.organizations);
        setError(null);
      })
      .catch((err) => {
        const message =
          err instanceof Error && err.message
            ? err.message
            : "Unable to load platform dashboard data.";
        setError(
          `Unable to load platform dashboard. Please sign in as Platform Admin and ensure the Keycloak role is assigned. Details: ${message}`
        );
      })
      .finally(() => setLoading(false));
  }, [logout, router, user]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="max-w-xl rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-800">
          <div className="font-semibold">Dashboard could not load</div>
          <p className="mt-2">{error}</p>
          <p className="mt-3 text-xs text-red-700">
            Use the Platform Admin login in Keycloak: username <strong>platform-admin</strong>, password <strong>platform-admin-password</strong>.
          </p>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-slate-500">
        No dashboard data available.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Platform Dashboard</h2>
        <p className="text-sm text-slate-500">
          Organizations, utilization, status, and active jobs across the platform
        </p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Organizations" value={stats.totalOrganizations} icon={Building2} />
        <StatCard
          title="Active Jobs"
          value={stats.activeJobs}
          icon={Zap}
          subtitle="Running now"
        />
        <StatCard
          title="Queries Today"
          value={stats.queriesToday.toLocaleString()}
          icon={Activity}
        />
        <StatCard
          title="Utilization"
          value={`${stats.utilizationPercent}%`}
          icon={TrendingUp}
          trend="Platform capacity"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Organizations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs font-medium uppercase text-slate-500">
                    <th className="pb-3 pr-4">Organization</th>
                    <th className="pb-3 pr-4">Plan</th>
                    <th className="pb-3 pr-4">Status</th>
                    <th className="pb-3 pr-4">Users</th>
                    <th className="pb-3">Queries/mo</th>
                  </tr>
                </thead>
                <tbody>
                  {organizations.map((org) => (
                    <tr key={org.id} className="border-b border-slate-50">
                      <td className="py-3 pr-4 font-medium text-slate-900">{org.name}</td>
                      <td className="py-3 pr-4 capitalize text-slate-600">
                        {org.plan.replace("_", " ")}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={org.status === "active" ? "success" : "warning"}>
                          {org.status}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 text-slate-600">{org.userCount}</td>
                      <td className="py-3 text-slate-600">
                        {org.queriesThisMonth.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {activeJobs.length === 0 && (
                <p className="text-sm text-slate-500">No active jobs right now.</p>
              )}
              {activeJobs.map((job) => (
                <div key={job.id} className="rounded-lg border border-slate-100 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-slate-900">{job.organization}</p>
                    <span className="text-xs text-slate-400">{job.startedAt}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{job.type}</p>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-indigo-600 transition-all"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                  <p className="mt-1 text-right text-xs text-slate-500">{job.progress}%</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
