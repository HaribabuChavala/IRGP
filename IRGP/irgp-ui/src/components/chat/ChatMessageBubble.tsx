"use client";

import { cn } from "@/lib/cn";
import { Bot, User } from "lucide-react";
import type { ChatMessage } from "@/lib/types";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

type ChartPoint = {
  label: string;
  value: number;
};

function parseNumericValue(value: string): number | null {
  if (!value) return null;
  const cleaned = value
    .replace(/[$,%\s]/g, "")
    .replace(/,/g, "")
    .trim();

  if (!cleaned) return null;

  const lower = cleaned.toLowerCase();
  let multiplier = 1;
  if (lower.endsWith("k")) {
    multiplier = 1000;
  } else if (lower.endsWith("m")) {
    multiplier = 1000000;
  }

  const normalized = lower.replace(/[kmb]/g, "");
  const num = Number(normalized);
  if (!Number.isFinite(num)) return null;

  return num * multiplier;
}

function extractChartData(rows: string[][] | undefined): ChartPoint[] | null {
  if (!rows || rows.length < 2) return null;

  const normalized = rows.slice(1).map((row) => row.map((cell) => (cell ?? "").trim()));
  const firstRow = rows[0].map((cell) => cell.trim().toLowerCase());

  if (firstRow[0] === "attribute" && firstRow.length >= 2) {
    const points = normalized
      .map((row) => ({ label: row[0] ?? "Item", value: parseNumericValue(row[1] ?? "") }))
      .filter((point): point is ChartPoint => point.value !== null);

    return points.length > 0 ? points.slice(0, 8) : null;
  }

  const header = rows[0];
  const labelIndex = header.findIndex((cell) => /label|name|category|region|segment|month|date|product/i.test(cell));
  const numericIndex = header.findIndex((cell, index) => index !== labelIndex && parseNumericValue(rows[1]?.[index] ?? "") !== null);

  if (labelIndex === -1 || numericIndex === -1) {
    const fallback = normalized
      .map((row) => ({ label: row[0] ?? "Item", value: parseNumericValue(row[1] ?? "") }))
      .filter((point): point is ChartPoint => point.value !== null);
    return fallback.length > 0 ? fallback.slice(0, 8) : null;
  }

  const points = normalized
    .map((row) => ({
      label: row[labelIndex] || `Item ${row[0] ?? ""}`,
      value: parseNumericValue(row[numericIndex] ?? ""),
    }))
    .filter((point): point is ChartPoint => point.value !== null)
    .slice(0, 8);

  return points.length > 0 ? points : null;
}

function buildPieArc(cx: number, cy: number, radius: number, startAngle: number, endAngle: number) {
  const start = {
    x: cx + radius * Math.cos((Math.PI / 180) * startAngle),
    y: cy + radius * Math.sin((Math.PI / 180) * startAngle),
  };
  const end = {
    x: cx + radius * Math.cos((Math.PI / 180) * endAngle),
    y: cy + radius * Math.sin((Math.PI / 180) * endAngle),
  };

  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;

  return `M ${cx} ${cy} L ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${end.x} ${end.y} Z`;
}

function ChartPreview({ data, type }: { data: ChartPoint[]; type: "bar" | "line" | "pie" }) {
  const width = 260;
  const height = 140;
  const maxValue = Math.max(...data.map((point) => point.value), 1);
  const palette = ["#4f46e5", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7", "#fb7185", "#64748b"];

  if (type === "bar") {
    const barWidth = width / data.length - 10;

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="h-36 w-full rounded-lg bg-slate-50 p-2">
        {data.map((point, index) => {
          const barHeight = (point.value / maxValue) * 90;
          const x = index * (width / data.length) + 8;
          const y = height - barHeight - 18;

          return (
            <g key={`${type}-${point.label}-${index}`}>
              <rect x={x} y={y} width={barWidth} height={barHeight} rx={4} fill={palette[index % palette.length]} opacity={0.9} />
              <text x={x + barWidth / 2} y={height - 4} textAnchor="middle" fontSize="9" fill="#475569">
                {point.label.slice(0, 4)}
              </text>
            </g>
          );
        })}
      </svg>
    );
  }

  if (type === "line") {
    const points = data
      .map((point, index) => {
        const x = (index / Math.max(data.length - 1, 1)) * (width - 18) + 10;
        const y = height - 18 - (point.value / maxValue) * (height - 42);
        return `${x},${y}`;
      })
      .join(" ");

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="h-36 w-full rounded-lg bg-slate-50 p-2">
        <polyline fill="none" stroke="#4f46e5" strokeWidth="3" points={points} />
        {data.map((point, index) => {
          const x = (index / Math.max(data.length - 1, 1)) * (width - 18) + 10;
          const y = height - 18 - (point.value / maxValue) * (height - 42);
          return <circle key={`${type}-${point.label}-${index}`} cx={x} cy={y} r={3} fill="#4f46e5" />;
        })}
      </svg>
    );
  }

  const total = data.reduce((sum, point) => sum + point.value, 0) || 1;
  let currentAngle = 0;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-36 w-full rounded-lg bg-slate-50 p-2">
      {data.map((point, index) => {
        const sliceAngle = (point.value / total) * 360;
        const path = buildPieArc(90, 70, 44, currentAngle, currentAngle + sliceAngle);
        currentAngle += sliceAngle;
        return <path key={`${type}-${point.label}-${index}`} d={path} fill={palette[index % palette.length]} stroke="#ffffff" strokeWidth="2" />;
      })}
      <circle cx="90" cy="70" r="22" fill="#f8fafc" />
      <text x="90" y="75" textAnchor="middle" fontSize="11" fontWeight="600" fill="#475569">
        {total}
      </text>
    </svg>
  );
}

function extractSqlQuery(content: string | undefined, sqlQuery: string | undefined): string | null {
  if (sqlQuery && sqlQuery.trim()) return sqlQuery.trim();
  if (!content) return null;

  const match = content.match(/Generated SQL:\s*([\s\S]*)/i);
  if (match && match[1]?.trim()) {
    return match[1].trim();
  }

  const sqlMatch = content.match(/SQL\s*\([^\)]*\):\s*([\s\S]*)/i);
  if (sqlMatch && sqlMatch[1]?.trim()) {
    return sqlMatch[1].trim();
  }

  return null;
}

export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === "user";
  const chartData = extractChartData(message.tableData);
  const sqlQuery = extractSqlQuery(message.content, message.sqlQuery);

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-indigo-600 text-white" : "bg-slate-200 text-slate-600"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className={cn("max-w-[80%] space-y-2", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "rounded-tr-sm bg-indigo-600 text-white"
              : "rounded-tl-sm border border-slate-200 bg-white text-slate-800 shadow-sm"
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {sqlQuery && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              SQL query
            </div>
            <pre className="overflow-x-auto whitespace-pre-wrap break-words text-xs text-slate-700">
              {sqlQuery}
            </pre>
          </div>
        )}

        {message.tableData && message.tableData.length > 0 && (
          <div className="space-y-3">
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-slate-50">
                  <tr>
                    {message.tableData[0].map((cell, i) => (
                      <th key={i} className="px-3 py-2 font-semibold text-slate-600">
                        {cell}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {message.tableData.slice(1).map((row, ri) => (
                    <tr key={ri} className="border-t border-slate-100">
                      {row.map((cell, ci) => (
                        <td key={ci} className="px-3 py-2 text-slate-700">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {chartData && (
              <div className="grid gap-3 md:grid-cols-3">
                {(["bar", "line", "pie"] as const).map((chartType) => (
                  <div key={chartType} className="rounded-xl border border-slate-200 bg-white p-2 shadow-sm">
                    <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                      {chartType} chart
                    </div>
                    <ChartPreview data={chartData} type={chartType} />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <p className="text-[10px] text-slate-400">
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
