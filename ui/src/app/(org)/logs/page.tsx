"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertTriangle, CheckCircle2, Info, Loader2, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import type { ExecutionLogEntry } from "@/lib/types";

function statusTone(status: string) {
  switch (status) {
    case "success":
      return "bg-emerald-100 text-emerald-700 ring-emerald-200";
    case "error":
      return "bg-rose-100 text-rose-700 ring-rose-200";
    case "warning":
      return "bg-amber-100 text-amber-700 ring-amber-200";
    default:
      return "bg-slate-100 text-slate-700 ring-slate-200";
  }
}

function StatusIcon({ status }: { status: string }) {
  if (status === "success") return <CheckCircle2 className="h-4 w-4" />;
  if (status === "error") return <XCircle className="h-4 w-4" />;
  if (status === "warning") return <AlertTriangle className="h-4 w-4" />;
  return <Info className="h-4 w-4" />;
}

export default function LogsPage() {
  const searchParams = useSearchParams();
  const [logs, setLogs] = useState<ExecutionLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const selectedJobId = searchParams.get("jobId") ?? "";

  useEffect(() => {
    api
      .executionLogs()
      .then((data) => setLogs(data.logs))
      .catch(() => setLogs([]))
      .finally(() => setLoading(false));
  }, []);

  const filteredLogs = useMemo(() => {
    if (!selectedJobId) return logs;
    return logs.filter((log) => log.jobId === selectedJobId || log.queryId === selectedJobId);
  }, [logs, selectedJobId]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Execution Logs</h2>
        <p className="text-sm text-slate-500">
          End-to-end observability for report generation, including the exact stage, engine, and failure message.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      ) : filteredLogs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
          {selectedJobId ? `No execution logs found for job ${selectedJobId}.` : "No execution logs yet for this organization."}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredLogs.map((log) => (
            <div key={log.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${statusTone(log.status)}`}>
                    <StatusIcon status={log.status} />
                    {log.status.toUpperCase()}
                  </span>
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    {log.stage}
                  </span>
                  {log.executionEngine && (
                    <span className="text-xs rounded-full bg-indigo-50 px-2 py-1 text-indigo-700">
                      {log.executionEngine}
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-500">
                  {new Date(log.createdAt).toLocaleString()}
                </div>
              </div>

              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-slate-500">Source</div>
                  <div className="mt-1 text-sm text-slate-700">{log.source}</div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-slate-500">Engine</div>
                  <div className="mt-1 text-sm text-slate-700">{log.executionEngine ?? "n/a"}</div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-slate-500">Query / Job</div>
                  <div className="mt-1 text-sm text-slate-700">{log.queryId ?? log.jobId ?? "n/a"}</div>
                </div>
              </div>

              <div className="mt-4">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Message</div>
                <div className="mt-1 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                  {log.message}
                </div>
              </div>

              {log.errorDetails && (
                <div className="mt-4">
                  <div className="text-[11px] uppercase tracking-wide text-slate-500">Exact error</div>
                  <div className="mt-1 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 whitespace-pre-wrap">
                    {log.errorDetails}
                  </div>
                </div>
              )}

              {log.context && Object.keys(log.context).length > 0 && (
                <div className="mt-4">
                  <div className="text-[11px] uppercase tracking-wide text-slate-500">Context</div>
                  <pre className="mt-1 max-h-52 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100 whitespace-pre-wrap">
                    {JSON.stringify(log.context, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
