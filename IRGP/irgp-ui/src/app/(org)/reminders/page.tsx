"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/lib/api";
import type { SubscriptionReminder } from "@/lib/types";

export default function RemindersPage() {
  const [reminders, setReminders] = useState<SubscriptionReminder[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .reminders()
      .then((data) => setReminders(data.reminders))
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
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Subscription Reminders</h2>
        <p className="text-sm text-slate-500">
          Renewal and usage reminders for your organization
        </p>
      </div>

      <div className="space-y-3">
        {reminders.length === 0 && (
          <p className="text-sm text-slate-500">No active reminders.</p>
        )}
        {reminders.map((r) => (
          <Card key={r.id}>
            <CardContent className="flex items-start gap-4 py-4">
              <div className="rounded-lg bg-amber-50 p-2">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
              </div>
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="warning">{r.plan.replace("_", " ")}</Badge>
                  <span className="text-xs text-slate-500">
                    {r.daysRemaining} days remaining
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-700">{r.message}</p>
                <p className="mt-2 text-xs text-slate-400">
                  Expires: {new Date(r.expiresAt).toLocaleDateString()}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
