"use client";

import { useEffect, useState } from "react";
import { Activity, Database, History, Loader2 } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/lib/api";
import type { DataSource, QueryHistoryItem } from "@/lib/types";

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [totalQueries, setTotalQueries] = useState(0);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([]);

  useEffect(() => {
    api
      .orgDashboard()
      .then((data) => {
        setTotalQueries(data.totalQueries);
        setDataSources(data.dataSources);
        setQueryHistory(data.queryHistory);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">User Dashboard</h2>
        <p className="text-sm text-slate-500">
          Queries per data source and execution history for your organization
        </p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Total Queries"
          value={totalQueries.toLocaleString()}
          subtitle="Across all data sources"
          icon={Activity}
        />
        <StatCard
          title="Data Sources"
          value={dataSources.length}
          subtitle="Connected and active"
          icon={Database}
        />
        <StatCard
          title="Recent Executions"
          value={queryHistory.length}
          subtitle="Saved in history"
          icon={History}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Queries per Data Source</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {dataSources.map((ds) => (
                <div key={ds.id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{ds.name}</p>
                    <p className="text-xs text-slate-500">{ds.type.toUpperCase()}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-slate-900">
                      {ds.queryCount.toLocaleString()}
                    </p>
                    <Badge variant={ds.status === "connected" ? "success" : "warning"}>
                      {ds.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Query History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {queryHistory.length === 0 && (
                <p className="text-sm text-slate-500">No queries executed yet.</p>
              )}
              {queryHistory.map((q) => (
                <div
                  key={q.id}
                  className="rounded-lg border border-slate-100 bg-slate-50/50 p-3"
                >
                  <p className="text-sm font-medium text-slate-900">{q.prompt}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span>{q.dataSourceName}</span>
                    <span>·</span>
                    <span>{new Date(q.executedAt).toLocaleString()}</span>
                    {q.rowCount != null && (
                      <>
                        <span>·</span>
                        <span>{q.rowCount} rows</span>
                      </>
                    )}
                  </div>
                  <Badge variant={q.status === "completed" ? "success" : "info"} className="mt-2">
                    {q.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
