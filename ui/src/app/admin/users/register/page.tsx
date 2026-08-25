"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Input, Label, Select } from "@/components/ui/Input";
import { api } from "@/lib/api";
import type { Organization, UserRole } from "@/lib/types";

export default function RegisterUsersPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [form, setForm] = useState({
    name: "",
    email: "",
    organizationId: "",
    role: "ORG_USER" as UserRole,
  });

  useEffect(() => {
    api.organizations().then((data) => {
      setOrganizations(data.organizations);
      if (data.organizations[0]) {
        setForm((prev) => ({ ...prev, organizationId: data.organizations[0].id }));
      }
    });
  }, []);

  const [result, setResult] = useState<{
    user?: {
      name?: string;
      username?: string;
      role?: string;
      email?: string;
      temporary_password?: string;
      delivery_status?: string;
      delivery_provider?: string;
    };
    note?: string;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);

    try {
      const apiResult = await api.registerUser(form);
      setResult(apiResult as typeof result);
      setNote((apiResult as { note?: string }).note ?? "");
      setSubmitted(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "User registration failed.";
      setErrorMessage(message);
      setSubmitted(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Register Admin & Users</h2>
        <p className="text-sm text-slate-500">
          Register organization admins and users. Admins can register data sources.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>User Registration</CardTitle>
          <CardDescription>
            Organization Admins manage data sources; Users generate reports.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {errorMessage ? (
            <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          {submitted ? (
            <div className="space-y-2 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800">
              <p>
                Login user ID <strong>{result?.user?.username ?? result?.user?.email?.split("@")[0] ?? form.email.split("@")[0]}</strong> registered as{" "}
                <strong>{(result?.user?.role ?? form.role).replace("_", " ")}</strong>.
              </p>
              <p>Full name: <strong>{result?.user?.name ?? form.name}</strong></p>
              {result?.user?.email && (
                <p>Email: <strong>{result.user.email}</strong></p>
              )}
              {result?.user?.username && (
                <p>Login username: <strong>{result.user.username}</strong></p>
              )}
              {result?.user?.delivery_status && (
                <p>
                  Delivery: <strong>{result.user.delivery_status}</strong> via <strong>{result.user.delivery_provider ?? "mock"}</strong>
                </p>
              )}
              {result?.user?.temporary_password && (
                <p>
                  Temporary password: <strong>{result.user.temporary_password}</strong>
                </p>
              )}
              {note && <p className="text-emerald-700">{note}</p>}
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Jane Doe"
                />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="jane@acme.com"
                />
              </div>
              <div>
                <Label htmlFor="organization">Organization</Label>
                <Select
                  id="organization"
                  value={form.organizationId}
                  onChange={(e) => setForm({ ...form, organizationId: e.target.value })}
                >
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="role">Role</Label>
                <Select
                  id="role"
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
                >
                  <option value="ORG_ADMIN">Organization Admin</option>
                  <option value="ORG_USER">Organization User</option>
                </Select>
              </div>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Registering..." : "Register User"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
