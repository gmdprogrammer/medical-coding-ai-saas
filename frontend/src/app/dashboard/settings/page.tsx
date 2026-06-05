"use client";
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";
import { User, Lock, CreditCard, Loader2, CheckCircle2, ShieldAlert } from "lucide-react";
import { useAuthStore } from "@/lib/auth";
import { authApi, codingApi } from "@/lib/api";
import Link from "next/link";
import { cn } from "@/lib/utils";

// Profile Schema
const profileSchema = z.object({
  full_name: z.string().min(2, "Name must be at least 2 characters"),
  organization: z.string().optional(),
});
type ProfileFormData = z.infer<typeof profileSchema>;

// Password Schema
const passwordSchema = z.object({
  current_password: z.string().min(1, "Current password required"),
  new_password: z.string()
    .min(8, "New password must be at least 8 characters")
    .regex(/[A-Z]/, "Must contain uppercase")
    .regex(/[0-9]/, "Must contain a number"),
  confirm_password: z.string().min(1, "Please confirm password"),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
});
type PasswordFormData = z.infer<typeof passwordSchema>;

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const [activeTab, setActiveTab] = useState<"profile" | "security" | "billing">("profile");
  const [profileLoading, setProfileLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [sessionCount, setSessionCount] = useState<number | null>(null);

  // Profile Form
  const { register: regProfile, handleSubmit: handleProfileSubmit, formState: { errors: profileErrors }, reset: resetProfile } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name || "",
      organization: user?.organization || "",
    },
  });

  // Password Form
  const { register: regPassword, handleSubmit: handlePasswordSubmit, formState: { errors: passwordErrors }, reset: resetPassword } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  // Pre-load default values when user is fetched/updated
  useEffect(() => {
    if (user) {
      resetProfile({
        full_name: user.full_name,
        organization: user.organization || "",
      });

      // Load session usage count for billing
      codingApi.getSessions(1, 1)
        .then((data) => setSessionCount(data.total))
        .catch(() => setSessionCount(0));
    }
  }, [user, resetProfile]);

  const onUpdateProfile = async (data: ProfileFormData) => {
    setProfileLoading(true);
    try {
      const updatedUser = await authApi.updateProfile(data.full_name, data.organization || undefined);
      setUser(updatedUser);
      toast.success("Profile updated successfully!");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to update profile";
      toast.error(msg);
    } finally {
      setProfileLoading(false);
    }
  };

  const onChangePassword = async (data: PasswordFormData) => {
    setPasswordLoading(true);
    try {
      await authApi.changePassword(data.current_password, data.new_password);
      resetPassword();
      toast.success("Password updated successfully!");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to change password";
      toast.error(msg);
    } finally {
      setPasswordLoading(false);
    }
  };

  const tabs = [
    { id: "profile", label: "My Profile", icon: User },
    { id: "security", label: "Security & Access", icon: Lock },
    { id: "billing", label: "Billing & Plans", icon: CreditCard },
  ] as const;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Account Settings</h1>
        <p className="text-gray-500 mt-1">
          Manage your profile information, password security, and active subscription plan.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Navigation Sidebar */}
        <div className="md:col-span-1 flex flex-row md:flex-col gap-1 overflow-x-auto pb-2 md:pb-0">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors w-full whitespace-nowrap",
                  activeTab === tab.id
                    ? "bg-medical-50 text-medical-700"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                )}
              >
                <Icon className="h-4.5 w-4.5 flex-shrink-0" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Content Pane */}
        <div className="md:col-span-3">
          {/* Profile Tab */}
          {activeTab === "profile" && (
            <div className="card space-y-6">
              <div>
                <h2 className="text-base font-semibold text-gray-900">General Information</h2>
                <p className="text-xs text-gray-400 mt-0.5">Customize your personal detail settings.</p>
              </div>

              <form onSubmit={handleProfileSubmit(onUpdateProfile)} className="space-y-4">
                <div>
                  <label className="label">Full Name</label>
                  <input
                    {...regProfile("full_name")}
                    type="text"
                    className="input"
                    placeholder="Dr. Jane Smith"
                  />
                  {profileErrors.full_name && (
                    <p className="mt-1 text-xs text-red-500">{profileErrors.full_name.message}</p>
                  )}
                </div>

                <div>
                  <label className="label">Email Address</label>
                  <input
                    type="email"
                    className="input bg-gray-50 text-gray-500 border-gray-200 cursor-not-allowed"
                    value={user?.email || ""}
                    disabled
                  />
                  <p className="mt-1 text-[11px] text-gray-400">
                    To update your verified email address, please contact our support team.
                  </p>
                </div>

                <div>
                  <label className="label">Organization / Hospital</label>
                  <input
                    {...regProfile("organization")}
                    type="text"
                    className="input"
                    placeholder="City General Hospital"
                  />
                </div>

                <div className="flex justify-end pt-2 border-t border-gray-100">
                  <button type="submit" className="btn-primary" disabled={profileLoading}>
                    {profileLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    {profileLoading ? "Saving Changes..." : "Save Changes"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Security Tab */}
          {activeTab === "security" && (
            <div className="card space-y-6">
              <div>
                <h2 className="text-base font-semibold text-gray-900">Change Password</h2>
                <p className="text-xs text-gray-400 mt-0.5">Ensure your account is using a strong password.</p>
              </div>

              <form onSubmit={handlePasswordSubmit(onChangePassword)} className="space-y-4">
                <div>
                  <label className="label">Current Password</label>
                  <input
                    {...regPassword("current_password")}
                    type="password"
                    placeholder="••••••••"
                    className="input"
                    autoComplete="current-password"
                  />
                  {passwordErrors.current_password && (
                    <p className="mt-1 text-xs text-red-500">{passwordErrors.current_password.message}</p>
                  )}
                </div>

                <div>
                  <label className="label">New Password</label>
                  <input
                    {...regPassword("new_password")}
                    type="password"
                    placeholder="••••••••"
                    className="input"
                    autoComplete="new-password"
                  />
                  {passwordErrors.new_password && (
                    <p className="mt-1 text-xs text-red-500">{passwordErrors.new_password.message}</p>
                  )}
                  <p className="mt-1 text-xs text-gray-400">Min. 8 characters, 1 uppercase, 1 number</p>
                </div>

                <div>
                  <label className="label">Confirm New Password</label>
                  <input
                    {...regPassword("confirm_password")}
                    type="password"
                    placeholder="••••••••"
                    className="input"
                    autoComplete="new-password"
                  />
                  {passwordErrors.confirm_password && (
                    <p className="mt-1 text-xs text-red-500">{passwordErrors.confirm_password.message}</p>
                  )}
                </div>

                <div className="flex justify-end pt-2 border-t border-gray-100">
                  <button type="submit" className="btn-primary" disabled={passwordLoading}>
                    {passwordLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    {passwordLoading ? "Updating Password..." : "Update Password"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Billing Tab */}
          {activeTab === "billing" && (
            <div className="card space-y-6">
              <div>
                <h2 className="text-base font-semibold text-gray-900">Subscription Plan</h2>
                <p className="text-xs text-gray-400 mt-0.5">Manage your monthly credits and billing settings.</p>
              </div>

              {/* Active Plan Card */}
              <div className="rounded-xl border border-medical-200 bg-medical-50/40 p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <span className="badge bg-medical-600 text-white border-transparent text-[10px] uppercase font-bold mb-1.5">
                    Active Plan
                  </span>
                  <h3 className="text-lg font-bold text-gray-900">Developer Free Tier</h3>
                  <p className="text-sm text-gray-500 mt-0.5">For individual developers and small clinics trying out AI coding.</p>
                </div>
                <Link href="/pricing" className="btn-primary text-center whitespace-nowrap self-start sm:self-center">
                  Upgrade to Pro
                </Link>
              </div>

              {/* Usage Meter Detail */}
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm font-medium">
                  <span className="text-gray-700">Monthly Analyzer Credits</span>
                  <span className="text-gray-900">{sessionCount ?? 0} / 50 sessions used</span>
                </div>
                <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden border border-gray-200/50">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-700",
                      (sessionCount ?? 0) >= 45 ? "bg-red-500" : (sessionCount ?? 0) >= 35 ? "bg-amber-500" : "bg-medical-600"
                    )}
                    style={{ width: `${Math.min(100, ((sessionCount ?? 0) / 50) * 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-400 flex items-center gap-1.5">
                  <ShieldAlert className="h-3.5 w-3.5 text-gray-400" />
                  Your usage quota resets automatically on the 1st of every month. Upgrading to a paid plan unlocks unlimited coding sessions.
                </p>
              </div>

              {/* Features List */}
              <div className="border-t border-gray-100 pt-6">
                <h4 className="text-xs font-bold text-gray-900 uppercase tracking-wider mb-3">Included in Free Tier:</h4>
                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-600">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" /> 50 AI analyses / mo
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" /> HIPAA-safe PHI removal
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" /> ICD-10 & CPT recommendations
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" /> Admin audit dashboard
                  </li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
