"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { ReportChat } from "@/components/chat/ReportChat";
import { api } from "@/lib/api";
import type { DataSource } from "@/lib/types";

export default function ReportsPage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .dataSources()
      .then((data) => setDataSources(data.dataSources))
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
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Instant Report Generation</h2>
        <p className="text-sm text-slate-500">
          Select a data source and describe your report in plain language
        </p>
      </div>
      {dataSources.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
          No data sources registered. An organization admin must add a data source first.
        </p>
      ) : (
        <ReportChat dataSources={dataSources} />
      )}
    </div>
  );
}
