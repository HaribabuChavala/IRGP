"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input, Label, Select } from "@/components/ui/Input";
import { api } from "@/lib/api";
import type { SubscriptionPlan } from "@/lib/types";

export default function RegisterOrganizationPage() {
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [existingOrganizations, setExistingOrganizations] = useState<string[]>([]);
  const [orgNameStatus, setOrgNameStatus] = useState<{ valid: boolean; message: string } | null>(null);
  const [emailStatus, setEmailStatus] = useState<{ valid: boolean; message: string } | null>(null);
  const [result, setResult] = useState<{
    organizationName: string;
    emailDelivery: string;
    createdUsers: Array<{
      email: string;
      temporary_password: string;
      username: string;
      role: string;
      delivery_status: string;
      delivery_provider: string;
    }>;
  } | null>(null);

  const [form, setForm] = useState({
    organization_name: "",
    contact_email: "",
    region: "",
    plan: "free" as SubscriptionPlan,
    orgAdminName: "",
    orgAdminEmail: "",
    orgAdminUsername: "",
    userName: "",
    userEmail: "",
    userUsername: "",
  });

  useEffect(() => {
    let isMounted = true;

    api.organizations()
      .then((data) => {
        if (!isMounted) return;
        setExistingOrganizations(data.organizations.map((org) => org.name));
      })
      .catch(() => {
        if (isMounted) setExistingOrganizations([]);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const name = form.organization_name.trim();
    if (!name) {
      setOrgNameStatus(null);
      return;
    }

    if (name.length < 2) {
      setOrgNameStatus({ valid: false, message: "Name must be at least 2 characters." });
      return;
    }

    const duplicated = existingOrganizations.some(
      (existingName) => existingName.toLowerCase() === name.toLowerCase()
    );

    setOrgNameStatus({
      valid: !duplicated,
      message: duplicated ? "Organization name already exists." : "Name available.",
    });
  }, [form.organization_name, existingOrganizations]);

  useEffect(() => {
    const adminEmail = form.orgAdminEmail.trim().toLowerCase();
    const userEmail = form.userEmail.trim().toLowerCase();

    if (!adminEmail || !userEmail) {
      setEmailStatus(null);
      return;
    }

    if (adminEmail === userEmail) {
      setEmailStatus({
        valid: false,
        message: "Admin email and invited user email must be different.",
      });
      return;
    }

    setEmailStatus({ valid: true, message: "Emails are different." });
  }, [form.orgAdminEmail, form.userEmail]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);

    if (orgNameStatus && !orgNameStatus.valid) {
      setErrorMessage("Please choose a unique organization name.");
      setSubmitting(false);
      return;
    }

    if (emailStatus && !emailStatus.valid) {
      setErrorMessage("Admin email and invited user email must be different.");
      setSubmitting(false);
      return;
    }

    try {
      const response = await api.onboardOrganization({
        organization_name: form.organization_name,
        contact_email: form.contact_email,
        region: form.region,
        plan: form.plan,
        organization_admin: {
          email: form.orgAdminEmail,
          username: form.orgAdminUsername || form.orgAdminEmail.split("@")[0],
          full_name: form.orgAdminName,
          role: "ORG_ADMIN",
        },
        users: form.userEmail
          ? [
              {
                email: form.userEmail,
                username: form.userUsername || form.userEmail.split("@")[0],
                full_name: form.userName,
                role: "ORG_USER",
              },
            ]
          : [],
      });

      setResult({
        organizationName: response.organization.name,
        emailDelivery: response.email_delivery,
        createdUsers: response.created_users.map((user) => ({
          email: user.email,
          temporary_password: user.temporary_password,
          username: user.username,
          role: user.role,
          delivery_status: user.delivery_status,
          delivery_provider: user.delivery_provider,
        })),
      });
      setSubmitted(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Organization onboarding failed.";
      setErrorMessage(message);
      setSubmitted(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Onboard Organization</h2>
        <p className="text-sm text-slate-500">
          Register the organization, assign the first admin, and invite users with temporary passwords.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Organization + Access Setup</CardTitle>
        </CardHeader>
        <CardContent>
          {errorMessage ? (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          {submitted && result ? (
            <div className="space-y-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
              <div className="font-semibold">Onboarding complete</div>
              <p>
                Organization <strong>{result.organizationName}</strong> was onboarded successfully.
              </p>
              <p>
                Email delivery status: <strong>{result.emailDelivery}</strong>
              </p>

              <div className="space-y-3">
                {result.createdUsers.map((member) => (
                  <div key={member.email} className="rounded border border-emerald-200 bg-white p-3">
                    <div className="font-medium">{member.username} ({member.role})</div>
                    <div className="text-xs text-slate-600">{member.email}</div>
                    <div className="mt-2 text-xs">
                      Delivery: <strong>{member.delivery_status}</strong> via <strong>{member.delivery_provider}</strong>
                    </div>
                    <div className="mt-1 text-xs">
                      Temporary password: <strong>{member.temporary_password}</strong>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="md:col-span-2">
                  <Label htmlFor="organization_name">Organization Name</Label>
                  <Input
                    id="organization_name"
                    required
                    value={form.organization_name}
                    onChange={(e) => setForm({ ...form, organization_name: e.target.value })}
                    placeholder="Acme Financial"
                  />
                  {orgNameStatus ? (
                    <p
                      className={`mt-2 text-xs ${
                        orgNameStatus.valid ? "text-emerald-600" : "text-rose-600"
                      }`}
                    >
                      {orgNameStatus.message}
                    </p>
                  ) : null}
                </div>
                <div>
                  <Label htmlFor="contact_email">Contact Email</Label>
                  <Input
                    id="contact_email"
                    type="email"
                    required
                    value={form.contact_email}
                    onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                    placeholder="admin@acme.com"
                  />
                </div>
                <div>
                  <Label htmlFor="region">Region</Label>
                  <Input
                    id="region"
                    required
                    value={form.region}
                    onChange={(e) => setForm({ ...form, region: e.target.value })}
                    placeholder="us-east-1"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label htmlFor="plan">Subscription Plan</Label>
                  <Select
                    id="plan"
                    value={form.plan}
                    onChange={(e) => setForm({ ...form, plan: e.target.value as SubscriptionPlan })}
                  >
                    <option value="free">Free</option>
                    <option value="half_year">Half Year ($499 / 6 months)</option>
                    <option value="year">Annual ($899 / 12 months)</option>
                  </Select>
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 p-4">
                <h3 className="mb-3 font-medium text-slate-900">Organization Admin</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="orgAdminName">Full Name</Label>
                    <Input
                      id="orgAdminName"
                      required
                      value={form.orgAdminName}
                      onChange={(e) => setForm({ ...form, orgAdminName: e.target.value })}
                      placeholder="Taylor Smith"
                    />
                  </div>
                  <div>
                    <Label htmlFor="orgAdminUsername">Username</Label>
                    <Input
                      id="orgAdminUsername"
                      required
                      value={form.orgAdminUsername}
                      onChange={(e) => setForm({ ...form, orgAdminUsername: e.target.value })}
                      placeholder="taylor"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Label htmlFor="orgAdminEmail">Admin Email</Label>
                    <Input
                      id="orgAdminEmail"
                      type="email"
                      required
                      value={form.orgAdminEmail}
                      onChange={(e) => setForm({ ...form, orgAdminEmail: e.target.value })}
                      placeholder="admin@acme.com"
                    />
                    {emailStatus && form.userEmail ? (
                      <p
                        className={`mt-2 text-xs ${
                          emailStatus.valid ? "text-emerald-600" : "text-rose-600"
                        }`}
                      >
                        {emailStatus.message}
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 p-4">
                <h3 className="mb-3 font-medium text-slate-900">Additional User Invite</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="userName">Full Name</Label>
                    <Input
                      id="userName"
                      value={form.userName}
                      onChange={(e) => setForm({ ...form, userName: e.target.value })}
                      placeholder="Jordan Lee"
                    />
                  </div>
                  <div>
                    <Label htmlFor="userUsername">Username</Label>
                    <Input
                      id="userUsername"
                      value={form.userUsername}
                      onChange={(e) => setForm({ ...form, userUsername: e.target.value })}
                      placeholder="jordan"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Label htmlFor="userEmail">User Email</Label>
                    <Input
                      id="userEmail"
                      type="email"
                      value={form.userEmail}
                      onChange={(e) => setForm({ ...form, userEmail: e.target.value })}
                      placeholder="analyst@acme.com"
                    />
                    {emailStatus && form.orgAdminEmail ? (
                      <p
                        className={`mt-2 text-xs ${
                          emailStatus.valid ? "text-emerald-600" : "text-rose-600"
                        }`}
                      >
                        {emailStatus.message}
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>

              <Button type="submit" disabled={submitting}>
                {submitting ? "Onboarding..." : "Onboard Organization"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
