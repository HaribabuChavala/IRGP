"use client";

import { useEffect, useState } from "react";
import { Bell, FileText, CreditCard, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/lib/api";
import type { Notification } from "@/lib/types";

const iconMap = {
  report: FileText,
  subscription: CreditCard,
  system: Bell,
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .notifications()
      .then((data) => setNotifications(data.notifications))
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
        <h2 className="text-lg font-semibold text-slate-900">Notifications</h2>
        <p className="text-sm text-slate-500">
          Reports generated and platform alerts for your account
        </p>
      </div>

      <div className="space-y-3">
        {notifications.length === 0 && (
          <p className="text-sm text-slate-500">No notifications yet.</p>
        )}
        {notifications.map((n) => {
          const Icon = iconMap[n.type];
          return (
            <Card key={n.id} className={!n.read ? "border-indigo-200 bg-indigo-50/20" : ""}>
              <CardContent className="flex items-start gap-4 py-4">
                <div className="rounded-lg bg-slate-100 p-2">
                  <Icon className="h-5 w-5 text-slate-600" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-slate-900">{n.title}</p>
                    {!n.read && <Badge variant="info">New</Badge>}
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{n.message}</p>
                  <p className="mt-2 text-xs text-slate-400">
                    {new Date(n.createdAt).toLocaleString()}
                  </p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
