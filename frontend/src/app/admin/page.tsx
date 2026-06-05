"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Users, Activity, Clock, CheckCircle, Star, Shield } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { adminApi } from "@/lib/api";
import { useAuthStore, useIsAdmin } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import type { DashboardStats } from "@/types";
import { formatDate, cn } from "@/lib/utils";

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: string | number; icon: any; color: string
}) {
  return (
    <div className="card flex items-center gap-4">
      <div className={cn("h-12 w-12 rounded-xl flex items-center justify-center flex-shrink-0", color)}>
        <Icon className="h-6 w-6 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const isAdmin = useIsAdmin();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pending, setPending] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [tab, setTab] = useState<"overview" | "sessions" | "users">("overview");

  useEffect(() => {
    if (!isAdmin) return;
    adminApi.getDashboard().then(setStats);
    adminApi.getPendingSessions().then(setPending);
    adminApi.getUsers().then((d) => setUsers(d.users));
  }, [isAdmin]);

  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full text-center card py-12">
          <div className="h-16 w-16 bg-red-50 text-red-600 rounded-full flex items-center justify-center mx-auto mb-6 border border-red-100">
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-sm text-gray-500 mb-8 leading-relaxed">
            You do not have administrative privileges to access this area. If you believe this is an error, please contact your administrator.
          </p>
          <button
            onClick={() => router.replace("/dashboard")}
            className="btn-primary w-full text-center"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Navigation />
      <main className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Shield className="h-6 w-6 text-medical-600" /> Admin Dashboard
            </h1>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-6 p-1 bg-gray-100 rounded-lg w-fit">
            {(["overview", "sessions", "users"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  "px-4 py-1.5 rounded-md text-sm font-medium capitalize transition-colors",
                  tab === t ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"
                )}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Overview tab */}
          {tab === "overview" && stats && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <StatCard label="Total users"      value={stats.total_users}      icon={Users}    color="bg-medical-600" />
                <StatCard label="Total sessions"   value={stats.total_sessions}   icon={Activity} color="bg-purple-600" />
                <StatCard label="Sessions today"   value={stats.sessions_today}   icon={Clock}    color="bg-indigo-600" />
                <StatCard label="Pending reviews"  value={stats.pending_reviews}  icon={CheckCircle} color="bg-orange-500" />
                <StatCard label="Avg confidence"   value={`${Math.round(stats.avg_confidence * 100)}%`}  icon={Star}  color="bg-green-600" />
                <StatCard label="User accuracy"    value={`${Math.round(stats.accuracy_rate * 100)}%`}   icon={Shield} color="bg-teal-600" />
              </div>

              <div className="card">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Key Metrics</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={[
                    { name: "Avg Confidence", value: Math.round(stats.avg_confidence * 100) },
                    { name: "Accuracy Rate",  value: Math.round(stats.accuracy_rate * 100) },
                  ]}>
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(v: any) => `${v}%`} />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      <Cell fill="#2563eb" />
                      <Cell fill="#10b981" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Sessions tab */}
          {tab === "sessions" && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-700">Pending Reviews ({pending.length})</h2>
              {pending.length === 0 ? (
                <div className="card text-center py-10 text-gray-400">No sessions pending review</div>
              ) : (
                pending.map((s) => (
                  <div key={s.id} className="card">
                    <p className="text-sm text-gray-700 mb-2 line-clamp-2">{s.clinical_summary}</p>
                    <div className="flex gap-3 text-xs text-gray-500 mb-3">
                      <span>ICD avg: {Math.round((s.avg_icd_confidence || 0) * 100)}%</span>
                      <span>CPT avg: {Math.round((s.avg_cpt_confidence || 0) * 100)}%</span>
                      <span>{formatDate(s.created_at)}</span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => adminApi.reviewSession(s.id, "approved").then(() => setPending(p => p.filter(x => x.id !== s.id)))}
                        className="btn-primary text-xs px-3 py-1"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => adminApi.reviewSession(s.id, "needs_revision").then(() => setPending(p => p.filter(x => x.id !== s.id)))}
                        className="btn-secondary text-xs px-3 py-1"
                      >
                        Needs revision
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Users tab */}
          {tab === "users" && (
            <div className="card overflow-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-xs font-medium text-gray-500">
                    <th className="pb-3 pr-4">Name</th>
                    <th className="pb-3 pr-4">Email</th>
                    <th className="pb-3 pr-4">Role</th>
                    <th className="pb-3 pr-4">Status</th>
                    <th className="pb-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {users.map((u) => (
                    <tr key={u.id} className="py-2">
                      <td className="py-3 pr-4 font-medium text-gray-900">{u.full_name}</td>
                      <td className="py-3 pr-4 text-gray-500">{u.email}</td>
                      <td className="py-3 pr-4">
                        <span className="badge bg-medical-50 text-medical-700 border-medical-200">{u.role}</span>
                      </td>
                      <td className="py-3 pr-4">
                        <span className={cn("badge", u.is_active ? "bg-green-50 text-green-700 border-green-200" : "bg-red-50 text-red-700 border-red-200")}>
                          {u.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => adminApi.updateUser(u.id, { is_active: !u.is_active }).then(() =>
                            setUsers(us => us.map(x => x.id === u.id ? { ...x, is_active: !u.is_active } : x))
                          )}
                          className="text-xs text-medical-600 hover:underline"
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
