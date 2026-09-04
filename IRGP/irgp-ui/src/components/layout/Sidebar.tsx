"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import type { NavItem } from "@/config/navigation";
import { FileBarChart2, LogOut } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";

interface SidebarProps {
  items: NavItem[];
  title: string;
  subtitle?: string;
  isAdmin?: boolean;
}

export function Sidebar({ items, title, subtitle, isAdmin }: SidebarProps) {
  const pathname = usePathname();
  const { logout } = useAuth();

  const visibleItems = items.filter(
    (item) => !item.adminOnly || isAdmin
  );

  return (
    <aside className="flex h-full w-64 flex-col border-r border-slate-200 bg-slate-950 text-white">
      <div className="flex items-center gap-3 border-b border-slate-800 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600">
          <FileBarChart2 className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight">{title}</p>
          {subtitle && (
            <p className="text-xs text-slate-400">{subtitle}</p>
          )}
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {visibleItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 p-4">
        <button
          type="button"
          onClick={() => logout()}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
