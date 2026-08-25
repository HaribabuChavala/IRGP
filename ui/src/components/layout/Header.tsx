"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";

interface HeaderProps {
  title: string;
  description?: string;
  userName?: string;
  userRole?: string;
  notificationCount?: number;
}

export function Header({
  title,
  description,
  userName = "Demo User",
  userRole = "Organization User",
  notificationCount = 0,
}: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-8 py-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        {description && (
          <p className="mt-0.5 text-sm text-slate-500">{description}</p>
        )}
      </div>

      <div className="flex items-center gap-4">
        <Link
          href="/notifications"
          className="relative rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
        >
          <Bell className="h-5 w-5" />
          {notificationCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
              {notificationCount}
            </span>
          )}
        </Link>

        <div className="flex items-center gap-3 border-l border-slate-200 pl-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-sm font-semibold text-indigo-700">
            {userName.charAt(0).toUpperCase()}
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-slate-900">{userName}</p>
            <Badge variant="info" className="mt-0.5">
              {userRole}
            </Badge>
          </div>
        </div>
      </div>
    </header>
  );
}
