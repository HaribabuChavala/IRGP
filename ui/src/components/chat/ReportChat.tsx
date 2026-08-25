"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Input";
import { ChatMessageBubble } from "@/components/chat/ChatMessageBubble";
import { ExportActions } from "@/components/chat/ExportActions";
import { api, streamReportJob } from "@/lib/api";
import type { ChatMessage, DataSource } from "@/lib/types";

interface ReportChatProps {
  dataSources: DataSource[];
}

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Welcome to Instant Report Generation. Select a data source above, then describe the report you need in plain language. I'll generate results here and you can export to Excel, PDF, or CSV.",
  timestamp: new Date().toISOString(),
};

export function ReportChat({ dataSources }: ReportChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [selectedSource, setSelectedSource] = useState(dataSources[0]?.id ?? "");
  const [isGenerating, setIsGenerating] = useState(false);
  const [progressMessage, setProgressMessage] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const activeSource = dataSources.find((ds) => ds.id === selectedSource);
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.exportable);

  useEffect(() => {
    setSelectedSource(dataSources[0]?.id ?? "");
  }, [dataSources]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isGenerating, progressMessage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !activeSource || isGenerating) return;

    const prompt = input.trim();
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: prompt,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsGenerating(true);
    setProgressMessage("Starting report generation...");

    try {
      const { jobId } = await api.generateReport(prompt, activeSource.id);
      setActiveJobId(jobId);

      await streamReportJob(jobId, (event) => {
        setProgressMessage(event.message || `Progress: ${event.progress}%`);

        if (event.status === "completed" && event.content) {
          const sqlSection = event.sqlQuery
            ? `\n\nSQL (${(event.sqlDialect ?? "ansi").toUpperCase()}):\n${event.sqlQuery}`
            : "";
          const response: ChatMessage = {
            id: jobId,
            role: "assistant",
            content: `${event.content}${sqlSection}\n\nHere is a preview of the results:`,
            timestamp: new Date().toISOString(),
            exportable: true,
            tableData: event.tableData,
          };
          setMessages((prev) => [...prev, response]);
        }

        if (event.status === "failed") {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: event.message || "Report generation failed.",
              timestamp: new Date().toISOString(),
            },
          ]);
        }
      });

      setIsGenerating(false);
      setProgressMessage("");
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: error instanceof Error ? error.message : "Failed to generate report.",
          timestamp: new Date().toISOString(),
        },
      ]);
      setIsGenerating(false);
      setProgressMessage("");
    }
  };

  return (
    <div className="flex h-[calc(100vh-12rem)] flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center gap-4 border-b border-slate-100 px-5 py-4">
        <label htmlFor="data-source" className="text-sm font-medium text-slate-700">
          Data Source
        </label>
        <Select
          id="data-source"
          value={selectedSource}
          onChange={(e) => setSelectedSource(e.target.value)}
          className="max-w-xs"
        >
          {dataSources.map((ds) => (
            <option key={ds.id} value={ds.id}>
              {ds.name} ({ds.type.toUpperCase()})
            </option>
          ))}
        </Select>
        {activeSource && (
          <span className="text-xs text-slate-400">Status: {activeSource.status}</span>
        )}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {messages.map((msg) => (
          <ChatMessageBubble key={msg.id} message={msg} />
        ))}
        {isGenerating && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            {progressMessage || "Generating report..."}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {lastAssistant && activeJobId && (
        <div className="border-t border-slate-100 px-5 py-3">
          <ExportActions jobId={activeJobId} />
        </div>
      )}

      <form onSubmit={handleSubmit} className="border-t border-slate-100 p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe the report you want to generate..."
            disabled={isGenerating || !selectedSource}
            className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50"
          />
          <Button type="submit" disabled={!input.trim() || isGenerating || !selectedSource} size="lg">
            {isGenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Generate
          </Button>
        </div>
      </form>
    </div>
  );
}
