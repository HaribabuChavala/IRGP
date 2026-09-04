"use client";

import { type FormEvent, useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import type { BillingOrganizationState } from "@/lib/types";

export default function AdminBillingPage() {
  const [organizationId, setOrganizationId] = useState("org-acme");
  const [status, setStatus] = useState<"active" | "inactive">("active");
  const [region, setRegion] = useState("US");
  const [plan, setPlan] = useState("year");
  const [reason, setReason] = useState("Manual approval granted by IRGP admin.");
  const [submittedState, setSubmittedState] = useState<BillingOrganizationState | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await api.updateOrganizationBillingState(organizationId, {
        status,
        reason,
        updated_by: "IRGP_ADMIN",
        region,
        plan,
      });
      setSubmittedState(response);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Organization billing control</h2>
        <p className="text-sm text-slate-500">IRGP admin controls for manual activation and suspension.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Set access state</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Organization ID</label>
                <input
                  value={organizationId}
                  onChange={(event) => setOrganizationId(event.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-0 focus:border-indigo-500"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Status</label>
                  <select
                    value={status}
                    onChange={(event) => setStatus(event.target.value as "active" | "inactive")}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500"
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Region</label>
                  <select
                    value={region}
                    onChange={(event) => setRegion(event.target.value)}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500"
                  >
                    <option value="US">US</option>
                    <option value="UK">UK</option>
                    <option value="AE">UAE</option>
                    <option value="IN">IND</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Plan</label>
                <select
                  value={plan}
                  onChange={(event) => setPlan(event.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500"
                >
                  <option value="free">Free</option>
                  <option value="half_year">Half year</option>
                  <option value="year">Year</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Reason</label>
                <textarea
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  rows={4}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500"
                />
              </div>

              <Button type="submit" disabled={loading} className="w-full">
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  "Save billing state"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Last admin update</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {submittedState ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Status</span>
                  <Badge variant={submittedState.status === "active" ? "success" : "error"}>{submittedState.status}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Access</span>
                  <span className="font-medium text-slate-900">{submittedState.access_enabled ? "Enabled" : "Blocked"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Region</span>
                  <span className="font-medium text-slate-900">{submittedState.region ?? "US"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Plan</span>
                  <span className="font-medium text-slate-900">{submittedState.plan ?? "year"}</span>
                </div>
                <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                  <div className="mb-2 flex items-center gap-2 font-medium text-slate-900">
                    <ShieldCheck className="h-4 w-4 text-indigo-600" />
                    Latest note
                  </div>
                  <p>{submittedState.reason ?? "No comment provided."}</p>
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500">No update submitted yet. Use the form to activate or suspend an organization.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
