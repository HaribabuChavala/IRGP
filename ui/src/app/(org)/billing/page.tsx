"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, CreditCard, Loader2, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import type { BillingOrganizationState, BillingReminderRecord, InvoiceRecord } from "@/lib/types";

const organizationId = "org-acme";

function statusVariant(status: string) {
  switch (status.toLowerCase()) {
    case "active":
      return "success";
    case "pending":
    case "due_soon":
      return "warning";
    case "inactive":
    case "overdue":
    case "suspended":
      return "error";
    default:
      return "info";
  }
}

export default function BillingPage() {
  const [billingState, setBillingState] = useState<BillingOrganizationState | null>(null);
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [reminders, setReminders] = useState<BillingReminderRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.billingOrganization(organizationId),
      api.billingInvoices(organizationId),
      api.billingReminders(15),
    ])
      .then(([state, invoiceData, reminderData]) => {
        setBillingState(state);
        setInvoices(invoiceData.invoices ?? []);
        setReminders(reminderData.reminders ?? []);
      })
      .finally(() => setLoading(false));
  }, []);

  const totalDue = useMemo(
    () => invoices.filter((invoice) => invoice.status !== "paid").reduce((sum, invoice) => sum + Number(invoice.amount ?? 0), 0),
    [invoices]
  );

  if (loading || !billingState) {
    return (
      <div className="flex min-h-[200px] items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Billing overview</h2>
          <p className="text-sm text-slate-500">Organization {organizationId}</p>
        </div>
        <Button variant="outline" size="sm">Export invoice list</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-3 py-5">
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Access</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{billingState.status}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 py-5">
            <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
              <CreditCard className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Payment</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{billingState.payment_status ?? "unpaid"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 py-5">
            <div className="rounded-lg bg-amber-50 p-2 text-amber-600">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Due</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{new Intl.NumberFormat("en-US", { style: "currency", currency: billingState.region === "UK" ? "GBP" : "USD" }).format(totalDue)}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-3 py-5">
            <div className="rounded-lg bg-sky-50 p-2 text-sky-600">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Invoices</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{billingState.invoice_count ?? invoices.length}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <Card>
          <CardHeader>
            <CardTitle>Invoices</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto p-0">
            <table className="min-w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-6 py-3">Invoice</th>
                  <th className="px-6 py-3">Country</th>
                  <th className="px-6 py-3">Amount</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Due</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.id} className="border-t border-slate-100">
                    <td className="px-6 py-3 font-medium text-slate-900">{invoice.id}</td>
                    <td className="px-6 py-3">{invoice.country ?? billingState.region ?? "US"}</td>
                    <td className="px-6 py-3">{new Intl.NumberFormat("en-US", { style: "currency", currency: invoice.currency ?? "USD" }).format(invoice.amount)}</td>
                    <td className="px-6 py-3"><Badge variant={statusVariant(invoice.status)}>{invoice.status}</Badge></td>
                    <td className="px-6 py-3">{invoice.due_at ? new Date(invoice.due_at).toLocaleDateString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Account status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500">Manual status</span>
              <Badge variant={statusVariant(billingState.manual_status ?? billingState.status)}>{billingState.manual_status ?? billingState.status}</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500">Plan</span>
              <span className="font-medium text-slate-900">{billingState.plan ?? "year"}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500">Region</span>
              <span className="font-medium text-slate-900">{billingState.region ?? "US"}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500">Access enabled</span>
              <span className="font-medium text-slate-900">{billingState.access_enabled ? "Yes" : "No"}</span>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
              <div className="font-medium text-slate-900">Last update</div>
              <div className="mt-1">{billingState.updated_at ? new Date(billingState.updated_at).toLocaleString() : "—"}</div>
              {billingState.reason && <p className="mt-2 text-xs text-slate-500">{billingState.reason}</p>}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upcoming reminders</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {reminders.length === 0 && <p className="text-sm text-slate-500">No payment reminders for the next 15 days.</p>}
          {reminders.map((reminder) => (
            <div key={reminder.id} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
              <div>
                <p className="text-sm font-medium text-slate-900">{reminder.message}</p>
                <p className="mt-1 text-xs text-slate-500">Due {new Date(reminder.due_at).toLocaleDateString()} • {reminder.days_remaining} days remaining</p>
              </div>
              <Badge variant={statusVariant(reminder.status)}>{reminder.status}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
