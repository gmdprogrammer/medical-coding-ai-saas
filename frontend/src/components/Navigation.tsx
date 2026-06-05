"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, LayoutDashboard, History, Settings, ShieldCheck, LogOut, Menu, X } from "lucide-react";
import { useState, useEffect } from "react";
import { useAuthStore, useIsAdmin } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { codingApi } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/dashboard",       label: "Code Analyzer",   icon: LayoutDashboard },
  { href: "/dashboard/history", label: "History",       icon: History },
  { href: "/dashboard/settings", label: "Settings",       icon: Settings },
];

const ADMIN_ITEMS = [
  { href: "/admin", label: "Admin Panel", icon: ShieldCheck },
];

export default function Navigation() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const isAdmin = useIsAdmin();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sessionCount, setSessionCount] = useState<number | null>(null);

  const items = [...NAV_ITEMS, ...(isAdmin ? ADMIN_ITEMS : [])];

  useEffect(() => {
    if (user) {
      codingApi.getSessions(1, 1)
        .then((data) => {
          setSessionCount(data.total);
        })
        .catch(() => {
          setSessionCount(0);
        });
    }
  }, [user, pathname]); // Re-fetch count when pathname changes (e.g. user ran another analysis)

  return (
    <>
      {/* Sidebar — desktop */}
      <aside className="hidden md:flex flex-col w-60 min-h-screen border-r border-gray-200 bg-white flex-shrink-0">
        <div className="flex items-center gap-2 px-5 py-5 border-b border-gray-100 flex-shrink-0">
          <Activity className="h-6 w-6 text-medical-600 flex-shrink-0" />
          <span className="font-bold text-gray-900">Medical Coding AI</span>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {items.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                pathname === href || pathname.startsWith(href + "/")
                  ? "bg-medical-50 text-medical-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-gray-100 flex-shrink-0 bg-white">
          {sessionCount !== null && (
            <div className="px-3 py-2.5 mb-3 bg-neutral-50 rounded-lg border border-neutral-200/60 text-xs">
              <div className="flex justify-between font-medium text-neutral-700 mb-1">
                <span>Monthly Sessions</span>
                <span className="font-semibold">{sessionCount} / 50</span>
              </div>
              <div className="w-full h-1.5 bg-neutral-200 rounded-full overflow-hidden mb-1.5">
                <div 
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    sessionCount >= 45 ? "bg-red-500" : sessionCount >= 35 ? "bg-amber-500" : "bg-medical-600"
                  )}
                  style={{ width: `${Math.min(100, (sessionCount / 50) * 100)}%` }}
                />
              </div>
              <Link href="/pricing" className="text-[10px] text-medical-600 hover:underline font-semibold block text-right">
                Upgrade Plan →
              </Link>
            </div>
          )}

          <div className="px-3 py-2 mb-2">
            <p className="text-sm font-semibold text-gray-900 truncate">{user?.full_name}</p>
            <p className="text-xs text-gray-400 truncate">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-red-500 hover:bg-red-50 w-full transition-colors"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200 w-full flex-shrink-0">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-medical-600" />
          <span className="font-bold text-sm">Medical Coding AI</span>
        </div>
        <button onClick={() => setMobileOpen(!mobileOpen)} className="p-1 text-gray-500 hover:text-gray-900">
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-black/35 backdrop-blur-sm" onClick={() => setMobileOpen(false)}>
          <aside className="w-64 h-full bg-white shadow-xl flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100 flex-shrink-0">
              <Activity className="h-5 w-5 text-medical-600" />
              <span className="font-bold text-gray-900 text-sm">Medical Coding AI</span>
            </div>
            
            <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
              {items.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    pathname === href || pathname.startsWith(href + "/")
                      ? "bg-medical-50 text-medical-700"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  )}
                >
                  <Icon className="h-4 w-4" /> {label}
                </Link>
              ))}
            </nav>

            <div className="p-4 border-t border-gray-100 flex-shrink-0 bg-white">
              {sessionCount !== null && (
                <div className="p-2.5 mb-3 bg-neutral-50 rounded-lg border border-neutral-200/60 text-xs">
                  <div className="flex justify-between font-medium text-neutral-700 mb-1">
                    <span>Usage</span>
                    <span>{sessionCount} / 50</span>
                  </div>
                  <div className="w-full h-1 bg-neutral-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-medical-600 rounded-full"
                      style={{ width: `${Math.min(100, (sessionCount / 50) * 100)}%` }}
                    />
                  </div>
                </div>
              )}
              <div className="px-2 py-1.5 mb-2">
                <p className="text-xs font-semibold text-gray-900 truncate">{user?.full_name}</p>
                <p className="text-[10px] text-gray-400 truncate">{user?.email}</p>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-red-500 hover:bg-red-50 w-full transition-colors"
              >
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
