"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { FileSpreadsheet, FileText, Download } from "lucide-react";
import { downloadReportExport } from "@/lib/api";

interface ExportActionsProps {
  jobId: string;
  disabled?: boolean;
}

export function ExportActions({ jobId, disabled }: ExportActionsProps) {
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = async (format: "excel" | "pdf" | "csv") => {
    setExporting(format);
    try {
      await downloadReportExport(jobId, format);
    } catch (error) {
      alert(error instanceof Error ? error.message : "Export failed");
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium text-slate-500">Export:</span>
      <Button
        variant="outline"
        size="sm"
        disabled={disabled || exporting !== null}
        onClick={() => handleExport("excel")}
      >
        <FileSpreadsheet className="h-3.5 w-3.5" />
        {exporting === "excel" ? "Exporting..." : "Excel"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        disabled={disabled || exporting !== null}
        onClick={() => handleExport("pdf")}
      >
        <FileText className="h-3.5 w-3.5" />
        {exporting === "pdf" ? "Exporting..." : "PDF"}
      </Button>
      <Button
        variant="outline"
        size="sm"
        disabled={disabled || exporting !== null}
        onClick={() => handleExport("csv")}
      >
        <Download className="h-3.5 w-3.5" />
        {exporting === "csv" ? "Exporting..." : "CSV"}
      </Button>
    </div>
  );
}
