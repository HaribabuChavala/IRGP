"use client";

import { useEffect, useState } from "react";
import { Plus, Database, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Input, Label, Select } from "@/components/ui/Input";
import { isOrgAdmin, useAuth } from "@/components/auth/AuthProvider";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { DataSource, DataSourceType } from "@/lib/types";

export default function DataSourcesPage() {
  const { user } = useAuth();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testConnectionId, setTestConnectionId] = useState<string | null>(null);
  const [testMessage, setTestMessage] = useState<string>("");
  const [formError, setFormError] = useState<string>("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [submitted, setSubmitted] = useState(false);
  const [touchedFields, setTouchedFields] = useState<Partial<Record<string, boolean>>>({});

  const makeBlankForm = () => ({
    name: "",
    type: "oracle" as DataSourceType,
    connectionUrl: "",
    host: "",
    port: "",
    database: "",
    schema: "",
    filePath: "",
    username: "",
    password: "",
    accessMode: "read" as "read" | "write",
    readOnlyConfirmed: false,
  });

  const [form, setForm] = useState(makeBlankForm);

  const resetTestState = () => {
    setTestConnectionId(null);
    setTestMessage("");
    setWarnings([]);
  };

  const resetFormToBlank = () => {
    setForm(makeBlankForm());
    setTouchedFields({});
    setSubmitted(false);
    resetTestState();
    setFormError("");
  };

  const canManage = user ? isOrgAdmin(user.role) : false;

  const fieldExamples: Record<
    DataSourceType,
    {
      name: string;
      connectionUrl: string;
      host: string;
      port: string;
      databaseLabel: string;
      databasePlaceholder: string;
      schemaLabel: string;
      schemaPlaceholder: string;
      username: string;
      filePath: string;
    }
  > = {
    oracle: {
      name: "Oracle Finance",
      connectionUrl: "jdbc:oracle:thin:@//db.example.com:1521/ORCL",
      host: "db.example.com",
      port: "1521",
      databaseLabel: "Service Name / Database",
      databasePlaceholder: "ORCL",
      schemaLabel: "Schema / Owner (optional)",
      schemaPlaceholder: "APP_OWNER",
      username: "readonly_user",
      filePath: "/data/reports/sales.xlsx",
    },
    teradata: {
      name: "Teradata Warehouse",
      connectionUrl: "jdbc:teradata://teradata-lab/DBS_PORT=5432,DATABASE=teradata_lab",
      host: "teradata-lab",
      port: "5432",
      databaseLabel: "Database",
      databasePlaceholder: "teradata_lab",
      schemaLabel: "Schema (optional)",
      schemaPlaceholder: "public",
      username: "td_readonly",
      filePath: "/data/reports/sales.xlsx",
    },
    hive: {
      name: "Hive Analytics",
      connectionUrl: "jdbc:hive2://hive-server:10000/analytics",
      host: "hive-server",
      port: "10000",
      databaseLabel: "Database",
      databasePlaceholder: "analytics",
      schemaLabel: "Schema (optional)",
      schemaPlaceholder: "default",
      username: "hive_reader",
      filePath: "/data/reports/sales.xlsx",
    },
    jdbc: {
      name: "Generic JDBC Source",
      connectionUrl: "jdbc:postgresql://db.example.com:5432/reporting",
      host: "db.example.com",
      port: "5432",
      databaseLabel: "Database",
      databasePlaceholder: "reporting",
      schemaLabel: "Schema (optional)",
      schemaPlaceholder: "public",
      username: "report_reader",
      filePath: "/data/reports/sales.xlsx",
    },
    excel: {
      name: "Monthly Sales Excel",
      connectionUrl: "",
      host: "",
      port: "",
      databaseLabel: "Database",
      databasePlaceholder: "",
      schemaLabel: "Schema",
      schemaPlaceholder: "",
      username: "",
      filePath: "C:/data/reports/sales.xlsx",
    },
  };
  const currentExample = fieldExamples[form.type];

  const loadSources = () => {
    api
      .dataSources()
      .then((data) => setSources(data.dataSources))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadSources();
  }, []);

  const resetValidationState = () => {
    setSubmitted(false);
    setTouchedFields({});
    setFormError("");
  };

  const setField = (key: keyof typeof form, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    resetTestState();
    setFormError("");
  };

  const markTouched = (key: keyof typeof form) => {
    setTouchedFields((prev) => (prev[key] ? prev : { ...prev, [key]: true }));
  };

  const validateForm = (nextForm = form): string | null => {
    if (!nextForm.name.trim()) return "Data source name is required.";
    const nextName = nextForm.name.trim().toLowerCase();
    const duplicateName = nextName.length > 0 && sources.some((s) => (s.name || "").trim().toLowerCase() === nextName);
    if (duplicateName) return "Connection name already exists in this organization. Use a unique name.";
    if (!nextForm.readOnlyConfirmed || nextForm.accessMode !== "read") {
      return "Only read-only credentials are allowed for report generation.";
    }

    if (nextForm.type === "excel") {
      if (!nextForm.filePath.trim()) return "Excel file path is required.";
      return null;
    }

    const hasConnectionUrl = !!nextForm.connectionUrl.trim();
    if (!hasConnectionUrl && !nextForm.host.trim()) {
      return "Provide either a connection URL or host.";
    }
    if (!nextForm.database.trim()) {
      return "Database/Schema is required.";
    }
    if (!nextForm.username.trim() || !nextForm.password.trim()) {
      return "Username and password are required for non-file data sources.";
    }
    return null;
  };

  const validationError = validateForm();
  const normalizedName = form.name.trim().toLowerCase();
  const hasDuplicateName = normalizedName.length > 0 && sources.some((s) => (s.name || "").trim().toLowerCase() === normalizedName);
  const canTestConnection = !validationError && !testingConnection && !submitting;
  const canSaveDataSource = !validationError && !!testConnectionId && !testingConnection && !submitting;
  const testConnectionSucceeded = !!testConnectionId && !!testMessage;

  const fieldErrors: Partial<Record<keyof typeof form, string>> = {};
  if (!form.name.trim()) {
    fieldErrors.name = "Name is required.";
  } else if (hasDuplicateName) {
    fieldErrors.name = "Connection name already exists in this organization. Use a unique name.";
  }
  if (!form.readOnlyConfirmed || form.accessMode !== "read") {
    fieldErrors.readOnlyConfirmed = "Read-only confirmation is required.";
  }
  if (form.type === "excel") {
    if (!form.filePath.trim()) {
      fieldErrors.filePath = "Excel file path is required.";
    }
  } else {
    if (!form.connectionUrl.trim() && !form.host.trim()) {
      fieldErrors.connectionUrl = "Provide a connection URL or host.";
      fieldErrors.host = "Provide a host or connection URL.";
    }
    if (!form.database.trim()) {
      fieldErrors.database = "Database or service name is required.";
    }
    if (!form.username.trim()) {
      fieldErrors.username = "Read-only username is required.";
    }
    if (!form.password.trim()) {
      fieldErrors.password = "Password is required.";
    }
  }

  const showFieldError = (key: keyof typeof form) => Boolean((submitted || touchedFields[key]) && fieldErrors[key]);
  const fieldClassName = (key: keyof typeof form) =>
    cn(showFieldError(key) && "border-rose-300 bg-rose-50 focus:border-rose-500 focus:ring-rose-500/20");

  const isFormComplete = Object.keys(fieldErrors).length === 0;
  const canTestConnectionVisual = isFormComplete && !testingConnection && !submitting;
  const canSaveDataSourceVisual = isFormComplete && !!testConnectionId && !testingConnection && !submitting;

  const buildPayload = () => ({
    name: form.name.trim(),
    type: form.type,
    connectionUrl: form.type !== "excel" && form.connectionUrl.trim() ? form.connectionUrl.trim() : undefined,
    host: form.type !== "excel" && form.host.trim() ? form.host.trim() : undefined,
    port: form.type !== "excel" ? Number(form.port) || undefined : undefined,
    database: form.type !== "excel" ? form.database.trim() || undefined : undefined,
    schema: form.type !== "excel" ? form.schema.trim() || undefined : undefined,
    filePath: form.type === "excel" ? form.filePath.trim() : undefined,
    username: form.type !== "excel" ? form.username.trim() : undefined,
    password: form.type !== "excel" ? form.password : undefined,
    accessMode: form.accessMode,
  });

  const handleTestConnection = async () => {
    setSubmitted(true);
    const validation = validateForm();
    if (validation) {
      setFormError(validation);
      return;
    }

    setTestingConnection(true);
    setFormError("");
    try {
      const result = await api.testDataSourceConnection(buildPayload());
      setTestConnectionId(result.testConnectionId);
      setWarnings(result.warnings ?? []);
      setTestMessage(result.message || "Connection test succeeded.");
    } catch (error) {
      setTestConnectionId(null);
      setTestMessage("");
      setWarnings([]);
      setFormError(error instanceof Error ? error.message : "Connection test failed.");
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    const validation = validateForm();
    if (validation) {
      setFormError(validation);
      return;
    }
    if (!testConnectionId) {
      setFormError("Run Test Connection successfully before saving.");
      return;
    }

    setSubmitting(true);
    setFormError("");
    try {
      const result = await api.createDataSource({
        ...buildPayload(),
        testConnectionId,
      });
      setSources((prev) => [...prev, result.dataSource]);
      setForm({
        name: "",
        type: "oracle",
        connectionUrl: "",
        host: "",
        port: "",
        database: "",
        schema: "",
        filePath: "",
        username: "",
        password: "",
        accessMode: "read",
        readOnlyConfirmed: true,
      });
      resetValidationState();
      resetTestState();
      setShowForm(false);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Failed to save data source.");
    } finally {
      setSubmitting(false);
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Data Source Registration</h2>
          <p className="text-sm text-slate-500">
            Register Oracle, Teradata, Hive, or Excel file locations — Organization Admin only
          </p>
        </div>
        {canManage && (
          <Button
            onClick={() => {
              setShowForm(true);
              resetFormToBlank();
            }}
          >
            <Plus className="h-4 w-4" />
            Add Data Source
          </Button>
        )}
      </div>

      {showForm && canManage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/30 p-4">
          <div className="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-2xl">
            <Card className="border-0 shadow-none">
              <CardHeader>
                <div className="flex items-center justify-between gap-4">
                  <CardTitle>Register New Data Source</CardTitle>
                  <Button
                    type="button"
                    variant="outline"
                    className="!border-slate-200 !bg-white !text-slate-600 hover:!bg-slate-50"
                    onClick={() => {
                      setShowForm(false);
                      resetFormToBlank();
                    }}
                  >
                    Close
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  required
                  value={form.name}
                  onChange={(e) => setField("name", e.target.value)}
                  onBlur={() => markTouched("name")}
                  className={fieldClassName("name")}
                  placeholder={currentExample.name}
                />
                {showFieldError("name") && <p className="mt-1 text-xs text-rose-600">{fieldErrors.name}</p>}
              </div>
              <div>
                <Label htmlFor="type">Type</Label>
                <Select
                  id="type"
                  value={form.type}
                  onChange={(e) => setField("type", e.target.value as DataSourceType)}
                >
                  <option value="oracle">Oracle</option>
                  <option value="teradata">Teradata</option>
                  <option value="hive">Hive</option>
                  <option value="jdbc">Generic JDBC URL</option>
                  <option value="excel">Excel File</option>
                </Select>
              </div>
              {form.type !== "excel" ? (
                <>
                  <div className="sm:col-span-2">
                    <Label htmlFor="connectionUrl">Connection URL (recommended)</Label>
                    <Input
                      id="connectionUrl"
                      value={form.connectionUrl}
                      onChange={(e) => setField("connectionUrl", e.target.value)}
                      onBlur={() => markTouched("connectionUrl")}
                      className={fieldClassName("connectionUrl")}
                      placeholder={currentExample.connectionUrl}
                    />
                    <p className="mt-1 text-xs text-slate-400">Example: {currentExample.connectionUrl}</p>
                    {showFieldError("connectionUrl") && <p className="mt-1 text-xs text-rose-600">{fieldErrors.connectionUrl}</p>}
                  </div>
                  <div>
                    <Label htmlFor="host">Host</Label>
                    <Input
                      id="host"
                      value={form.host}
                      onChange={(e) => setField("host", e.target.value)}
                      onBlur={() => markTouched("host")}
                      className={fieldClassName("host")}
                      placeholder={currentExample.host}
                    />
                    {showFieldError("host") && <p className="mt-1 text-xs text-rose-600">{fieldErrors.host}</p>}
                  </div>
                  <div>
                    <Label htmlFor="port">Port</Label>
                    <Input
                      id="port"
                      type="number"
                      value={form.port}
                      onChange={(e) => setField("port", e.target.value)}
                      onBlur={() => markTouched("port")}
                      placeholder={currentExample.port}
                    />
                  </div>
                  <div>
                    <Label htmlFor="database">{currentExample.databaseLabel}</Label>
                    <Input
                      id="database"
                      required
                      value={form.database}
                      onChange={(e) => setField("database", e.target.value)}
                      onBlur={() => markTouched("database")}
                      className={fieldClassName("database")}
                      placeholder={currentExample.databasePlaceholder}
                    />
                    {showFieldError("database") && <p className="mt-1 text-xs text-rose-600">{fieldErrors.database}</p>}
                  </div>
                  <div>
                    <Label htmlFor="schema">{currentExample.schemaLabel}</Label>
                    <Input
                      id="schema"
                      value={form.schema}
                      onChange={(e) => setField("schema", e.target.value)}
                      onBlur={() => markTouched("schema")}
                      placeholder={currentExample.schemaPlaceholder}
                    />
                  </div>
                  <div>
                    <Label htmlFor="username">Read-only username</Label>
                    <Input
                      id="username"
                      required
                      value={form.username}
                      onChange={(e) => setField("username", e.target.value)}
                      onBlur={() => markTouched("username")}
                      className={fieldClassName("username")}
                      placeholder={currentExample.username}
                    />
                    {showFieldError("username") && <p className="mt-1 text-xs text-rose-600">{fieldErrors.username}</p>}
                  </div>
                  <div>
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      required
                      value={form.password}
                      onChange={(e) => setField("password", e.target.value)}
                      onBlur={() => markTouched("password")}
                      className={fieldClassName("password")}
                      placeholder="••••••••"
                      autoComplete="new-password"
                    />
                    {showFieldError("password") && <p className="mt-1 text-xs text-rose-600">{fieldErrors.password}</p>}
                  </div>
                </>
              ) : (
                <div className="sm:col-span-2">
                  <Label htmlFor="filePath">Excel File Location</Label>
                  <Input
                    id="filePath"
                    required
                    value={form.filePath}
                    onChange={(e) => setField("filePath", e.target.value)}
                    onBlur={() => markTouched("filePath")}
                    className={fieldClassName("filePath")}
                    placeholder={currentExample.filePath}
                  />
                  {showFieldError("filePath") && <p className="mt-1 text-xs text-rose-600">{fieldErrors.filePath}</p>}
                </div>
              )}
              <div className="sm:col-span-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                Store read-only credentials only. If credentials have write/DDL permissions, do not save them.
              </div>
              <label className="sm:col-span-2 flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={form.readOnlyConfirmed}
                  onChange={(e) => setField("readOnlyConfirmed", e.target.checked)}
                  onBlur={() => markTouched("readOnlyConfirmed")}
                />
                I confirm these credentials are read-only and safe for report retrieval.
              </label>
              {showFieldError("readOnlyConfirmed") && (
                <div className="sm:col-span-2 -mt-2 text-xs text-rose-600">{fieldErrors.readOnlyConfirmed}</div>
              )}
              {warnings.length > 0 && (
                <div className="sm:col-span-2 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-xs text-yellow-800">
                  {warnings.join(" ")}
                </div>
              )}
              {formError && (
                <div className="sm:col-span-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                  {formError}
                </div>
              )}
              {testMessage && testConnectionId && (
                <div className="sm:col-span-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-700">
                  {testMessage}
                </div>
              )}
              {!formError && !testConnectionId && validationError && (
                <div className="sm:col-span-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                  Complete all required fields to enable Test Connection.
                </div>
              )}
              {!formError && !validationError && !testConnectionId && (
                <div className="sm:col-span-2 rounded-lg border border-sky-200 bg-sky-50 p-3 text-xs text-sky-700">
                  Test Connection must succeed before Save Data Source is enabled.
                </div>
              )}
              <div className="flex gap-2 sm:col-span-2">
                <Button
                  type="button"
                  variant="outline"
                  className={cn(
                    "border transition-all",
                    testConnectionSucceeded
                      ? "!border-emerald-600 !bg-emerald-600 !text-white hover:!bg-emerald-500 hover:!text-white"
                      : canTestConnectionVisual
                        ? "!border-sky-600 !bg-sky-600 !text-white hover:!bg-sky-500 hover:!text-white shadow-sm"
                        : "!border-slate-200 !bg-slate-100 !text-slate-500"
                  )}
                  onClick={handleTestConnection}
                  disabled={!canTestConnection}
                >
                  {testingConnection ? "Testing..." : testConnectionSucceeded ? "Connection Verified" : "Test Connection"}
                </Button>
                <Button
                  type="submit"
                  variant="outline"
                  className={cn(
                    "border transition-all",
                    canSaveDataSourceVisual
                      ? "!border-indigo-600 !bg-indigo-600 !text-white hover:!bg-indigo-500 hover:!text-white shadow-sm"
                      : "!border-slate-200 !bg-slate-100 !text-slate-500"
                  )}
                  disabled={!canSaveDataSource}
                >
                  {submitting ? "Saving..." : "Save Data Source"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="!border-sky-600 !bg-sky-600 !text-white hover:!bg-sky-500 hover:!text-white"
                  onClick={() => {
                    setShowForm(false);
                    resetFormToBlank();
                  }}
                >
                  Cancel
                </Button>
              </div>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((ds) => (
          <Card key={ds.id}>
            <CardContent className="pt-5">
              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-indigo-50 p-2">
                  <Database className="h-5 w-5 text-indigo-600" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-slate-900">{ds.name}</p>
                  <p className="text-xs uppercase text-slate-500">{ds.type}</p>
                  {ds.connectionUrl && <p className="mt-1 break-all text-[11px] text-slate-400">{ds.connectionUrl}</p>}
                  <Badge variant={ds.status === "connected" ? "success" : "warning"} className="mt-2">
                    {ds.status}
                  </Badge>
                  <p className="mt-2 text-xs text-slate-400">
                    {ds.queryCount.toLocaleString()} queries executed
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
