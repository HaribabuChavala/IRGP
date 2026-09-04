"use client";

import { type FormEvent, useEffect, useState } from "react";
import { CreditCard, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import type { PaymentCheckoutResponse, SupportedRegion } from "@/lib/types";

export default function OrgPaymentsPage() {
  const [regions, setRegions] = useState<SupportedRegion[]>([]);
  const [paymentResponse, setPaymentResponse] = useState<PaymentCheckoutResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    organization_id: "org-acme",
    customer_email: "billing@irgp.local",
    country: "US",
    currency: "USD",
    amount: "1499",
    plan: "year",
    description: "IRGP annual subscription",
  });

  useEffect(() => {
    api.supportedPaymentRegions()
      .then((data) => setRegions(data.supported_regions ?? []))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const response = await api.createPaymentCheckout({
        organization_id: form.organization_id,
        customer_email: form.customer_email,
        country: form.country,
        currency: form.currency,
        amount: Number(form.amount) || 0,
        plan: form.plan,
        description: form.description,
      });
      setPaymentResponse(response);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Payment management</h2>
        <p className="text-sm text-slate-500">Checkout and regional payment configuration for supported countries.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>New payment checkout</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Organization ID</label>
                  <input
                    value={form.organization_id}
                    onChange={(event) => setForm((prev) => ({ ...prev, organization_id: event.target.value }))}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Customer email</label>
                  <input
                    type="email"
                    value={form.customer_email}
                    onChange={(event) => setForm((prev) => ({ ...prev, customer_email: event.target.value }))}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Country</label>
                  <select
                    value={form.country}
                    onChange={(event) => setForm((prev) => ({ ...prev, country: event.target.value }))}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
                  >
                    {regions.length === 0 ? <option value="US">US</option> : regions.map((region) => (
                      <option key={region.code} value={region.code}>{region.code}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Currency</label>
                  <input
                    value={form.currency}
                    onChange={(event) => setForm((prev) => ({ ...prev, currency: event.target.value }))}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Amount</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.amount}
                    onChange={(event) => setForm((prev) => ({ ...prev, amount: event.target.value }))}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Plan</label>
                <select
                  value={form.plan}
                  onChange={(event) => setForm((prev) => ({ ...prev, plan: event.target.value }))}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
                >
                  <option value="free">Free</option>
                  <option value="half_year">Half year</option>
                  <option value="year">Year</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Description</label>
                <textarea
                  rows={3}
                  value={form.description}
                  onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500"
                />
              </div>

              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating checkout...
                  </>
                ) : (
                  "Create payment checkout"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Supported regions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading payment regions...
              </div>
            ) : (
              regions.map((region) => (
                <div key={region.code} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <div>
                    <div className="font-medium text-slate-900">{region.name}</div>
                    <div className="text-xs text-slate-500">{region.code}</div>
                  </div>
                  <Badge variant="info">{region.currency}</Badge>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {paymentResponse && (
        <Card>
          <CardHeader>
            <CardTitle>Payment session</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-500">Status</span>
              <Badge variant={paymentResponse.status === "demo" ? "warning" : "success"}>{paymentResponse.status ?? "pending"}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-500">Provider</span>
              <span className="font-medium text-slate-900">{paymentResponse.provider ?? "stripe"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-500">Amount</span>
              <span className="font-medium text-slate-900">{paymentResponse.amount ?? 0} {paymentResponse.currency ?? "USD"}</span>
            </div>
            {paymentResponse.checkout_url && (
              <div className="rounded-lg border border-dashed border-indigo-200 bg-indigo-50 p-3">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium text-indigo-700">
                  <CreditCard className="h-4 w-4" />
                  Checkout URL
                </div>
                <a href={paymentResponse.checkout_url} className="break-all text-sm text-indigo-700 underline" target="_blank" rel="noreferrer">
                  {paymentResponse.checkout_url}
                </a>
              </div>
            )}
            {paymentResponse.message && <p className="text-sm text-slate-600">{paymentResponse.message}</p>}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
