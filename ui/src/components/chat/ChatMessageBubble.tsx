"use client";

import { cn } from "@/lib/cn";
import { Bot, User } from "lucide-react";
import type { ChatMessage } from "@/lib/types";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === "user";

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

        {message.tableData && message.tableData.length > 0 && (
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
        )}

        <p className="text-[10px] text-slate-400">
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
