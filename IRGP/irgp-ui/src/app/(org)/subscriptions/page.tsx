"use client";

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { isOrgAdmin, useAuth } from "@/components/auth/AuthProvider";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { SubscriptionPlan, SubscriptionPlanDetails } from "@/lib/types";

export default function SubscriptionsPage() {
  const { user } = useAuth();
  const [plans, setPlans] = useState<SubscriptionPlanDetails[]>([]);
  const [currentPlan, setCurrentPlan] = useState<SubscriptionPlan>("free");
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  const canUpgrade = user ? isOrgAdmin(user.role) : false;

  useEffect(() => {
    Promise.all([api.subscriptionPlans(), api.currentSubscription()])
      .then(([plansData, currentData]) => {
        setPlans(plansData.plans);
        setCurrentPlan(currentData.plan);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleUpgrade = async (plan: SubscriptionPlan) => {
    setUpgrading(plan);
    try {
      await api.upgradeSubscription(plan);
      setCurrentPlan(plan);
    } finally {
      setUpgrading(null);
    }
  };

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
        <h2 className="text-lg font-semibold text-slate-900">Subscriptions</h2>
        <p className="text-sm text-slate-500">
          Plan details and upgrade options — Organization Admin only
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = plan.id === currentPlan;
          return (
            <Card
              key={plan.id}
              className={cn(
                plan.highlighted && "ring-2 ring-indigo-500",
                isCurrent && "border-indigo-300 bg-indigo-50/30"
              )}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{plan.name}</CardTitle>
                  {isCurrent && <Badge variant="info">Current</Badge>}
                  {plan.highlighted && !isCurrent && (
                    <Badge variant="success">Popular</Badge>
                  )}
                </div>
                <p className="text-3xl font-bold text-slate-900">
                  {plan.price}
                  <span className="text-sm font-normal text-slate-500"> / {plan.period}</span>
                </p>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm text-slate-600">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                      {feature}
                    </li>
                  ))}
                </ul>
                {!isCurrent && canUpgrade && (
                  <Button
                    className="mt-6 w-full"
                    variant={plan.highlighted ? "primary" : "outline"}
                    disabled={upgrading === plan.id}
                    onClick={() => handleUpgrade(plan.id)}
                  >
                    {upgrading === plan.id ? "Upgrading..." : `Upgrade to ${plan.name}`}
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
